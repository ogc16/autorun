# AutoRun — Architecture

This document describes the technical design of AutoRun: components, request flows, the script
execution engine, scheduling, data model, and security model.

---

## 1. Overview

AutoRun is a **monolithic Spring Boot application** that manages the lifecycle of IT automation
scripts: *upload → parameterize → execute → observe → alert*. Two first-class clients share one
business layer:

- **Thymeleaf UI** — session-authenticated web pages for humans.
- **REST API** (`/api/**`) — JWT-authenticated JSON endpoints for automation / curl / integrations.

```
                 ┌──────────────────────────────────────────────┐
                 │                  Browser (UI)                 │
                 │        Thymeleaf + Bootstrap 5 + SSE          │
                 └──────────────────────┬───────────────────────┘
                                        │ session cookie (form login)
                                        ▼
┌──────────────┐   ┌─────────────────────────────────────────────┐   ┌──────────────────┐
│ curl / other │──▶│                  Spring MVC                  │──▶│  Quartz Scheduler │
│ (JWT)        │   │  SecurityConfig → Filters → Controllers      │   │  (cron triggers)  │
└──────────────┘   │                 (REST + MVC)                 │   └─────────┬────────┘
                   └───────┬──────────────┬──────────────┬────────┘             │ fire
                           ▼              ▼              ▼                      ▼
                   ┌──────────────┐ ┌──────────────┐ ┌───────────────────────────────┐
                   │ ScriptService│ │  JobService  │ │       ExecutionService        │
                   │  (files/DB)  │ │ (Quartz API) │ │   ProcessBuilder + threads    │
                   └──────┬───────┘ └──────┬───────┘ │   + SSE emitters + timeouts   │
                          │                │         └───────────────┬───────────────┘
                          ▼                ▼                         ▼
              ┌─────────────────┐ ┌───────────────┐        ┌──────────────────┐
              │   MySQL / H2    │ │  script files │        │  OS processes    │
              │   (JPA)         │ │  (storage dir)│        │  (py/sh/ps1/bat) │
              └─────────────────┘ └───────────────┘        └──────────────────┘
```

---

## 2. Package Structure

| Package | Responsibility |
|---|---|
| `com.autorun.config` | Seeding (`DataInitializer`), `@RestControllerAdvice` error handling, domain exceptions |
| `com.autorun.controller` | **REST controllers** (`/api/**`, JSON + JWT) and **view controllers** (Thymeleaf, session + CSRF) |
| `com.autorun.model` | JPA entities + enums (`Role`, `FileType`, `ExecutionStatus`, `TriggerType`, `JobStatus`) |
| `com.autorun.repository` | Spring Data JPA repositories |
| `com.autorun.security` | `SecurityConfig`, `JwtUtil`, `JwtAuthFilter`, `AppUserDetailsService` |
| `com.autorun.service` | Business logic: script CRUD, process execution, Quartz jobs, notifications, audit |
| `com.autorun.util` | `JsonUtil` (param/arg serialization), `ArgumentResolver` |

The controllers are deliberately thin — all business logic lives in services, which keeps both the
MVC and REST layers consistent and testable.

---

## 3. Script Execution Engine

The core of the product. See `ExecutionService`.

### 3.1 Command construction

The interpreter is selected from the uploaded file's extension and stored on the `Script` entity:

| `FileType` | Command shape |
|---|---|
| `PY` | `<python-interpreter> <path> <args…>` |
| `SH` | `bash <path> <args…>` |
| `PS1` | `powershell -NoProfile -ExecutionPolicy Bypass -File <path> <args…>` |
| `BAT` / `CMD` | `cmd /c <path> <args…>` |

The Python interpreter is configurable (`autorun.python-interpreter`, default `python`) so both
Windows and Linux hosts are supported.

### 3.2 Parameter → positional argument resolution

Scripts may declare parameters (name, label, required, default). On execution,
`ArgumentResolver` maps declared parameters to **positional CLI arguments** in declaration order:

```
missing required  → 422/400 "Missing required parameter 'x'"
missing optional  →  defaultValue (or omitted)
extra raw args    → appended after declared args
```

### 3.3 Process lifecycle

```
execute() ──▶ save ExecutionLog(RUNNING) ──▶ spawn daemon worker thread
                                                │
                                                ├─ build ProcessBuilder
                                                ├─ pb.start() ──▶ register in runningProcesses
                                                ├─ reader thread (stdout) ──▶ append + SSE "log"
                                                ├─ reader thread (stderr) ──▶ append + SSE "log"
                                                ├─ waitFor(timeout, SECONDS)
                                                │     ├─ false → destroyForcibly → TIMEOUT
                                                │     └─ true  → exitCode → SUCCESS | FAILED
                                                ├─ cancel flag set → CANCELLED
                                                └─ finalize: status, duration, logContent, notify, SSE "complete"
```

Key characteristics:

- **Async by default** — `POST …/execute` returns `202 Accepted` immediately; a daemon thread does
  the work, so one slow script never blocks the web tier.
- **Real-time logs** — stdout and stderr are read by dedicated threads and appended to an in-memory
  buffer, written incrementally to `data/logs/execution-<id>.log`, **and** pushed to connected SSE
  clients simultaneously.
- **Timeout** — `Process.waitFor(timeout, SECONDS)`; on expiry the process is force-killed
  (`destroyForcibly`) and marked `TIMEOUT`.
- **Cancellation** — a per-execution `AtomicBoolean` + `process.destroyForcibly()`.
- **Concurrency cap** — `autorun.max-concurrent-executions` (default 5) rejects with `409`
  when saturated.
- **Process cwd** — child processes run with the storage directory as working directory.

### 3.4 SSE live-log protocol

`GET /api/executions/{id}/stream` and `GET /executions/{id}/stream` (UI) both delegate to
`ExecutionService.stream(id)`. Emitters are registered in a `ConcurrentHashMap<Long, Set<SseEmitter>>`.

| Event | Data | When |
|---|---|---|
| `log` | `{"line": "...", "stream": "stdout"|"stderr"}` | each new line |
| `status` | `{"status": "...", "exitCode": 0}` | state changes |
| `complete` | `{"status": "...", "exitCode": 0}` | final state; emitter closed |

If a client connects to a finished execution, the full log is served via a `fetch` of the plain-text
log endpoint instead — the page never hangs.

---

## 4. Job Scheduling (Quartz)

`JobService` bridges JPA entities and the Quartz scheduler.

- Each `ScriptJob` maps to a Quartz `JobDetail` (`group="autorun-jobs"`, name `job-<id>`) plus a
  `CronTrigger`.
- `ScheduledJobExecutor extends QuartzJobBean` — Spring Boot's autowire-capable job factory injects
  `ExecutionService` via `@Autowired` setter even though Quartz instantiates the class reflectively.
- On create/edit, the trigger is (re)scheduled; `pause` / `resume` toggle the Quartz trigger;
  `delete` unschedules and removes it.
- `run-now` calls `scheduler.triggerJob(...)` for immediate fire.
- Fired jobs load fresh state from the DB, so a paused/disabled job never runs.
- The job store is in-memory by default (triggers re-created from DB rows on restart); swap to the
  JDBC job store for clustered setups (see `docs/DEPLOYMENT.md`).
- Next-fire-time is computed live from the `CronTrigger` and exposed for the UI / API.

**Cron validation & preview** use Quartz's `CronExpression` — invalid expressions are rejected with
`400`, and `GET /jobs/preview?cron=…` returns the next N fire times for the scheduler form.

---

## 5. Data Model

```
users(id, username, password[bcrypt], display_name, email, role, enabled, last_login_at, created_at)
scripts(id, name, filename, file_type, description, tags, parameters_json, size_bytes,
        storage_path, created_by→users, created_at, updated_at, last_executed_at)
script_jobs(id, name, description, script→scripts, cron_expression, time_zone, status,
            arguments_json, notify_on, enabled, created_by→users, created_at, last_run_at)
execution_logs(id, script→scripts, triggered_by, user→users, job→script_jobs, status, exit_code,
               started_at, finished_at, duration_ms, log_content[CLOB], log_file,
               arguments_json, notify_on, error_message)
audit_logs(id, user→users, action, target_type, target_id, details, ip_address, timestamp)
notification_settings(id=1, email_enabled, email_recipients, slack_enabled, slack_webhook, slack_channel)
```

- **Enums** stored as strings for readability (`@Enumerated(STRING)`).
- `parameters_json` / `arguments_json` are serialized with Jackson (`JsonUtil`) — keeps the schema
  simple while supporting free-form parameter maps.
- **Log files** live on disk (`data/logs`); the DB keeps a final snapshot (`log_content`) so history
  survives file pruning. `@Lob` + `@Transient` view fields keep the model JSON-friendly.

---

## 6. Security Model

Two authentication mechanisms, one authorization model.

### 6.1 Authentication

- **UI**: Spring Security form login (session, `JSESSIONID` cookie), custom `/login` page.
- **REST**: `JwtAuthFilter` (an `OncePerRequestFilter`) validates `Authorization: Bearer <token>`
  signed with HMAC-SHA (jjwt). Access token TTL 1h; refresh token TTL 24h (`/api/auth/refresh`).

### 6.2 Authorization (RBAC)

Roles are enforced twice — at the filter chain level and with `@PreAuthorize` method security:

| Capability | `ADMIN` | `TECH` |
|---|---|---|
| View dashboard / scripts / jobs / executions | ✅ | ✅ |
| Upload / edit scripts, run on demand, cancel | ✅ | ✅ |
| **Delete scripts** | ✅ | ❌ |
| Schedule / edit / pause / delete jobs | ✅ | ✅ |
| Manage users | ✅ | ❌ |
| Notification settings | ✅ | ❌ |
| Audit trail | all entries | own entries only |

`TECH` visibility of execution history and audit entries is enforced **server-side** in the services
(`ExecutionService.list` and `AuditService` filter by `user.id`).

### 6.3 CSRF & statelessness

- CSRF protection is **enabled for the UI** and automatically injected into Thymeleaf forms.
- `/api/**` is stateless (CSRF ignored, no session creation) — safe for JWT callers.

### 6.4 Data protection

- Passwords hashed with **BCrypt** (`BCryptPasswordEncoder`).
- JWT secret, SMTP credentials and DB credentials come from **environment variables**
  (`AUTORUN_JWT_SECRET`, `AUTORUN_SMTP_*`, `AUTORUN_DB_*`).
- Uploads: whitelisted extensions, 5 MB limit (`spring.servlet.multipart`), unique names.

---

## 7. Notifications

`NotificationService` is decoupled from execution — `ExecutionService` calls it only after an
execution finalizes, with the per-run `notifyOn` policy:

```
notifyOn = NEVER   → skip
notifyOn = ALWAYS  → send regardless of result
notifyOn = FAILURE → send only on FAILED / TIMEOUT
```

- **Slack**: HTTP POST to the incoming-webhook URL (RestClient), payload includes channel + text.
- **Email**: `JavaMailSender` with SMTP from env vars; body includes script, status, exit code,
  duration and the log file path.
- Failures to deliver alerts are logged but **never** break the execution pipeline.

---

## 8. Resilience & Operational Notes

- Daemon worker threads + `ConcurrentHashMap` registries keep execution independent of request threads.
- Unhandled exceptions funnel to `GlobalExceptionHandler` → consistent JSON error envelope with
  field-level validation details.
- `ddl-auto: update` is used for demo convenience; production should pin migrations (Flyway) —
  see roadmap.
- Health endpoint exposed at `/actuator/health` for container orchestration.

---

## 9. Key Design Decisions

| Decision | Rationale |
|---|---|
| Monolith (Spring Boot) | One deployable; right-sized for the feature set and demo-ability |
| Dual UI + REST on shared services | Recruiters/demos get a clickable UI *and* a scriptable API with zero duplication |
| In-memory log buffer + file + SSE | Three consumers (poll, download, live) with one incremental writer |
| Strings for params/args JSON | Flexible schemas without migration churn |
| Quartz over `@Scheduled` | Real cron triggers, pause/resume, next-fire preview, job-store upgrade path |
| ProcessBuilder over embedded exec | It *is* the feature — auditable, timeout-able, streamable OS process execution |

---

## 10. Test & CI Strategy

- GitHub Actions CI compiles and runs the test suite on every push (see `.github/workflows/ci.yml`).
- Suggested next steps: `@SpringBootTest` for the execution service (happy path, timeout, cancel),
  `@WebMvcTest` for RBAC on `/api/scripts`, and `MockMvc` tests for login + JWT issuance.
