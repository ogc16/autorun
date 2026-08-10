<div align="center">

# ⚡ AutoRun — Automation Script Runner

**A secure, centralized platform to upload, schedule, and execute IT automation scripts — with live logs, audit trails, and alerts.**

![Java](https://img.shields.io/badge/Java-17-ED8B00?logo=openjdk&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.3-6DB33F?logo=springboot&logoColor=white)
![Spring Security](https://img.shields.io/badge/Spring%20Security-JWT%20%2B%20RBAC-6DB33F?logo=springsecurity&logoColor=white)
![Quartz](https://img.shields.io/badge/Scheduler-Quartz-6DB33F)
![MySQL](https://img.shields.io/badge/Database-MySQL%208%20%7C%20H2-4479A1?logo=mysql&logoColor=white)
![CI](https://img.shields.io/github/actions/workflow/status/ogc16/autorun/ci.yml)
![License](https://img.shields.io/badge/License-MIT-blue)

Replaces manual, error-prone ops work (backups, patching, user provisioning) with a single
dashboard where every action is **auditable**, every run is **logged in real time**, and every
failure can **page you** via email or Slack.

</div>

---

## ✨ Features

| | |
|---|---|
| 📚 **Script Library** | Upload `.sh`, `.py`, `.ps1`, `.bat` / `.cmd` files with descriptions, tags, and **declared CLI parameters** that render as input fields on the Run form. |
| ▶️ **On-demand execution** | Click **Run** and watch **stdout/stderr stream live** (Server-Sent Events). Get an exit code, download the full log. A hard timeout kills hung scripts. |
| 🕐 **Quartz scheduler** | Cron-based recurring jobs (`0 0 2 ? * SUN`) with pause / resume / run-now and a live next-fire-time preview. |
| 🔐 **RBAC** | `ADMIN` (full control) vs `TECH` (run approved scripts, schedule jobs, view own logs). Enforced on both UI and REST API via Spring Security method security. |
| 🪪 **JWT auth** | Token-based REST API (`/api/**`) alongside session-based form login for the Thymeleaf UI. |
| 🛡️ **Audit trail** | Every run, upload, delete, schedule, and cancel is logged with actor, target, IP, and timestamp — exportable as CSV. |
| 🔔 **Alerts** | Email and Slack webhook notifications on script/job failure, with a per-run `FAILURE` / `ALWAYS` / `NEVER` policy. |
| 🐳 **Docker-ready** | Multi-stage `Dockerfile` + `docker-compose.yml` (MySQL 8), non-root runtime user. |

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Java 17, Spring Boot 3.3, Spring Security 6 |
| Script execution | `java.lang.ProcessBuilder` → Python / Bash / PowerShell / CMD |
| Scheduling | Quartz (cron triggers) |
| Persistence | Spring Data JPA / Hibernate — H2 (dev) or MySQL 8 (prod profile) |
| Frontend | Thymeleaf + Bootstrap 5, SSE live logs, no build step |
| Auth | JWT (jjwt) for REST, Spring Security sessions for the UI |
| Notifications | Spring JavaMail + Slack Incoming Webhooks |
| Build / Deploy | Maven, Docker Compose, GitHub Actions CI |

## 🚀 Quick Start

Prerequisites: **Java 17+** and **Maven** (or use the bundled `./mvnw` wrapper).

```bash
# build
mvn -DskipTests package

# run (H2 file database, nothing else required)
java -jar target/autorun-1.0.0.jar
```

Open **http://localhost:8080** and sign in:

| Role | Username | Password | Capabilities |
|---|---|---|---|
| Admin | `admin` | `admin123` | everything |
| Tech | `tech` | `tech123` | run scripts, schedule jobs, own logs only |

> ⚠️ **Change the seeded passwords and the `AUTORUN_JWT_SECRET` before any real deployment.**

### Docker + MySQL

```bash
docker compose up --build     # MySQL 8 + app
# open http://localhost:8080
```

## 🧪 Demo in 60 Seconds

1. Log in as **`admin`** → **Scripts** → open **`system_info`** → **Run Script**.
2. Watch the log stream live, see **SUCCESS / exit 0**.
3. **Scheduler** → **New Job** → script `collect_logs`, cron `0 */30 * * * ?`, click **Preview**, save.
4. Open **Audit** — every action, with actor + IP.
5. Try the REST API:

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r .accessToken)

curl -s -X POST http://localhost:8080/api/scripts/1/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"arguments":{"days":"3"}}'
```

Five sample scripts are seeded automatically — `system_info.cmd` and `collect_logs.py` run on
Windows; `backup.sh`, `patch_apt.sh`, `add_user.sh` target Linux servers / Docker.

## 📖 Documentation

| Document | Contents |
|---|---|
| [**REST API Reference**](docs/API.md) | Every endpoint, schema, error code, curl workflows |
| [**Architecture**](docs/ARCHITECTURE.md) | Design decisions, data model, execution engine, security model |
| [**User Guide**](docs/USER_GUIDE.md) | Roles, step-by-step walkthroughs, sample scripts |
| [**Deployment**](docs/DEPLOYMENT.md) | Docker/MySQL, environment variables, production hardening |

## 🗺️ Project Layout

```
src/main/java/com/autorun/
├── config/        DataInitializer (seed users/scripts), GlobalExceptionHandler
├── controller/    REST API (/api/**) + Thymeleaf view controllers
├── model/         User, Script, ScriptJob, ExecutionLog, AuditLog, enums
├── repository/    Spring Data JPA repositories
├── security/      JwtUtil, JwtAuthFilter, SecurityConfig, UserDetailsService
├── service/       ScriptService, ExecutionService, JobService, NotificationService, AuditService
└── util/          JSON helpers, argument resolution
src/main/resources/
├── scripts/       sample scripts bundled at startup
├── templates/     Thymeleaf pages (dashboard, scripts, jobs, executions, audit)
└── application.yml
```

## 🔒 Security Notes

- Scripts run with the privileges of the app process — deploy AutoRun **inside the Docker container
  as a non-root user** on an isolated host in production.
- Hard **10-minute timeout** and a **max-concurrent-executions** cap prevent runaway/hung processes.
- Uploads are restricted to a whitelist of extensions and a **5 MB** size limit.
- Passwords are **BCrypt-hashed**; the REST API is protected by short-lived **JWT** access tokens.

## 🗓️ Roadmap (v2)

- Lightweight Java **server agent** for remote / distributed execution
- Dashboard analytics (success-rate charts), Splunk / Jira integration
- Git-backed script version control

## 📄 License

[MIT](LICENSE)

---

*Built as a portfolio project: Automation · Systems Support · Cybersecurity.*
