# AutoRun — Automation Script Runner API Documentation

Version: 1.0.0 (Draft)
Base URL: `http://localhost:8080/api`
Format: JSON (`application/json`), Multipart for uploads
Authentication: JWT Bearer tokens (REST) / Spring Security session (UI)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Conventions](#2-conventions)
   - 2.1 Authentication
   - 2.2 Common Headers
   - 2.3 Pagination
   - 2.4 Error Format
   - 2.5 Roles (RBAC)
3. [Authentication & Users](#3-authentication--users)
   - `POST /auth/login`
   - `POST /auth/refresh`
   - `GET /auth/me`
   - `GET /users`
   - `POST /users`
   - `PUT /users/{id}`
   - `DELETE /users/{id}`
4. [Script Library](#4-script-library)
   - `POST /scripts`
   - `GET /scripts`
   - `GET /scripts/{id}`
   - `GET /scripts/{id}/content`
   - `PUT /scripts/{id}`
   - `DELETE /scripts/{id}`
5. [Script Execution](#5-script-execution)
   - `POST /scripts/{id}/execute`
   - `GET /executions`
   - `GET /executions/{id}`
   - `GET /executions/{id}/log`
   - `GET /executions/{id}/stream` (SSE — live logs)
   - `POST /executions/{id}/cancel`
6. [Scheduled Jobs (Quartz)](#6-scheduled-jobs-quartz)
   - `POST /jobs`
   - `GET /jobs`
   - `GET /jobs/{id}`
   - `PUT /jobs/{id}`
   - `DELETE /jobs/{id}`
   - `POST /jobs/{id}/pause`
   - `POST /jobs/{id}/resume`
   - `POST /jobs/{id}/run-now`
   - `GET /jobs/next-fire-times`
7. [Audit Logs](#7-audit-logs)
   - `GET /audit`
   - `GET /audit/export`
8. [Notification Settings](#8-notification-settings)
   - `GET /notifications/settings`
   - `PUT /notifications/settings`
   - `POST /notifications/test`
9. [Data Schemas](#9-data-schemas)
10. [Error Reference](#10-error-reference)
11. [End-to-End Workflows](#11-end-to-end-workflows)
12. [Roadmap: v2 Server Agents](#12-roadmap-v2-server-agents)

---

## 1. Overview

AutoRun is a web platform for IT automation. Admins and technicians upload scripts
(Python / Bash / PowerShell), execute them on demand with real-time log streaming,
schedule recurring jobs with cron expressions (Quartz), and receive email/Slack
alerts on failure — all protected by role-based access control and fully audited.

| Area | Technology |
|---|---|
| Backend | Java 17, Spring Boot 3, Spring Security |
| Execution | `java.lang.ProcessBuilder` → Python / Bash / PowerShell |
| Scheduling | Quartz (cron triggers) |
| Storage | PostgreSQL / MySQL (H2 for local dev), filesystem for scripts & logs |
| Auth | JWT (REST) + Session (UI), roles `ADMIN`, `TECH` |

---

## 2. Conventions

### 2.1 Authentication

Every endpoint except `/auth/login` requires a JWT Bearer token:

```
Authorization: Bearer <token>
```

`POST /auth/login` returns `accessToken` (short-lived, default 60 min) and
`refreshToken` (default 24 h). On expiry, exchange the refresh token via
`POST /auth/refresh`.

The UI (Thymeleaf) authenticates via a session cookie; the same role rules apply.

### 2.2 Common Headers

| Header | Value | Notes |
|---|---|---|
| `Authorization` | `Bearer <jwt>` | Required for all authenticated calls |
| `Content-Type` | `application/json` | For JSON bodies |
| `X-Request-Id` | UUID | Optional, echoed in logs for tracing |

Responses include `X-Audit-Id` when an action writes an audit record.

### 2.3 Pagination

List endpoints return paginated envelopes:

```json
{
  "content": [...],
  "page": 0,
  "size": 20,
  "totalElements": 42,
  "totalPages": 3
}
```

Query params: `page` (0-based), `size` (default 20, max 100), `sort=field,asc|desc`
(repeatable, e.g. `sort=createdAt,desc`).

### 2.4 Error Format

All errors use a consistent envelope:

```json
{
  "timestamp": "2026-08-11T10:00:00Z",
  "status": 400,
  "error": "Bad Request",
  "message": "cron expression '99 * * * * ?' is invalid",
  "path": "/api/jobs",
  "requestId": "3f2a..."
}
```

Field validation errors add `fieldErrors`:

```json
{
  "timestamp": "...",
  "status": 400,
  "error": "Validation Failed",
  "message": "Validation failed for request body",
  "fieldErrors": [
    { "field": "name", "message": "must not be blank" }
  ],
  "path": "/api/scripts"
}
```

### 2.5 Roles (RBAC)

| Capability | `ADMIN` | `TECH` |
|---|---|---|
| Login / view dashboard, scripts, jobs, logs | ✅ | ✅ |
| Run scripts on demand, cancel executions | ✅ | ✅ |
| Upload / edit scripts | ✅ | ✅ |
| **Delete scripts** | ✅ | ❌ |
| Create / edit / delete / pause / resume jobs | ✅ | ❌ |
| Manage users (create/edit/delete, assign roles) | ✅ | ❌ |
| View audit logs / export | ✅ | ✅* |

\* `TECH` may only see audit entries for their own actions.

Violations return `403 Forbidden`.

---

## 3. Authentication & Users

### POST `/auth/login`

Authenticate and receive JWT tokens.

**Request**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response `200 OK`**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiJ9...",
  "refreshToken": "eyJhbGciOiJIUzI1NiJ9...",
  "tokenType": "Bearer",
  "expiresIn": 3600,
  "user": {
    "id": 1,
    "username": "admin",
    "displayName": "System Admin",
    "email": "admin@example.com",
    "role": "ADMIN"
  }
}
```

**Errors:** `401` invalid credentials, `403` account disabled.

---

### POST `/auth/refresh`

Exchange a valid refresh token for a new access token.

**Request**
```json
{ "refreshToken": "eyJhbGciOiJIUzI1NiJ9..." }
```

**Response `200 OK`** — same shape as login.

**Errors:** `401` token invalid or expired.

---

### GET `/auth/me`

Return the currently authenticated user.

**Response `200 OK`** — user object (see schema §9.3).

**Roles:** `ADMIN`, `TECH`.

---

### GET `/users`

List users. Admin only.

**Query params:** `search` (username/email contains), pagination params.

**Response `200 OK`** — paginated list of user objects.

**Roles:** `ADMIN`.

---

### POST `/users`

Create a user. Admin only.

**Request**
```json
{
  "username": "j.smith",
  "password": "Temp#2026",
  "displayName": "Jane Smith",
  "email": "j.smith@company.com",
  "role": "TECH"
}
```

**Response `201 Created`** — created user (password never echoed).

**Errors:** `400` validation, `409` username/email already exists.

**Roles:** `ADMIN`.

---

### PUT `/users/{id}`

Update display name, email, role, or (optionally) password.

**Request**
```json
{
  "displayName": "Jane S.",
  "email": "jane@company.com",
  "role": "TECH",
  "password": "New#Pass2026"
}
```

`password` is optional — omit to leave unchanged.

**Response `200 OK`** — updated user.

**Roles:** `ADMIN`.

---

### DELETE `/users/{id}`

Disable/remove a user. Admins cannot delete themselves.

**Response `204 No Content`**

**Errors:** `400` cannot delete self, `404` not found.

**Roles:** `ADMIN`.

---

## 4. Script Library

### POST `/scripts`

Upload a new script. Multipart form-data.

**Form fields**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | `.py`, `.sh`, `.ps1`, `.bat`, `.cmd` (max 5 MB) |
| `name` | string | ✅ | Unique display name |
| `description` | string | ❌ | Purpose / notes |
| `tags` | string | ❌ | Comma-separated, e.g. `patching,backup` |
| `parameters` | string | ❌ | JSON array of parameter definitions (see below) |

`parameters` example — declares CLI args so the UI renders input fields:

```json
[
  { "name": "username", "label": "Username", "required": true, "description": "User to provision" },
  { "name": "shell", "label": "Default shell", "required": false, "defaultValue": "/bin/bash" }
]
```

**Response `201 Created`**
```json
{
  "id": 12,
  "name": "add_user",
  "filename": "add_user.sh",
  "fileType": "SH",
  "description": "Provision a new system user",
  "tags": ["user-provisioning", "identity"],
  "parameters": [...],
  "createdBy": { "id": 1, "username": "admin" },
  "createdAt": "2026-08-11T09:12:00Z",
  "sizeBytes": 1420
}
```

**Errors:** `400` invalid type/empty file/duplicate name, `413` too large.

**Roles:** `ADMIN`, `TECH`.

---

### GET `/scripts`

List scripts.

**Query params:** `search` (name/description contains), `tag`, pagination/sort.

**Response `200 OK`** — paginated list of script summaries (no file content).

**Roles:** `ADMIN`, `TECH`.

---

### GET `/scripts/{id}`

Full script metadata including tag and parameter definitions.

**Response `200 OK`** — script object (schema §9.1).

**Errors:** `404` not found.

---

### GET `/scripts/{id}/content`

Return the raw script file body as `text/plain`.

**Response `200 OK`** — file bytes with `Content-Disposition: inline`.

**Roles:** `ADMIN`, `TECH`.

---

### PUT `/scripts/{id}`

Update metadata and/or replace the file (multipart, same fields as `POST /scripts`; only send what changed).

**Response `200 OK`** — updated script.

**Roles:** `ADMIN`, `TECH`.

---

### DELETE `/scripts/{id}`

Delete a script and its stored file. Any scheduled jobs referencing it are removed.

**Response `204 No Content`**

**Errors:** `404` not found.

**Roles:** `ADMIN` only.

---

## 5. Script Execution

### POST `/scripts/{id}/execute`

Run a script on demand. Returns immediately; the execution runs asynchronously.

**Request**
```json
{
  "arguments": {
    "username": "mkoss",
    "shell": "/bin/bash"
  },
  "env": { "DEPLOY_ENV": "prod" },
  "timeoutSeconds": 300,
  "notifyOn": "FAILURE"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `arguments` | object | `{}` | Values for declared parameters; passed to the script in declaration order |
| `env` | object | `{}` | Extra environment variables for the child process |
| `timeoutSeconds` | int | 600 | Hard kill after this long; `0` = no timeout |
| `notifyOn` | enum | `FAILURE` | `NEVER`, `FAILURE`, `ALWAYS` |

**Response `202 Accepted`**
```json
{
  "id": 87,
  "script": { "id": 12, "name": "add_user" },
  "status": "RUNNING",
  "startedAt": "2026-08-11T09:15:00Z",
  "exitCode": null,
  "logUrl": "/api/executions/87/log",
  "streamUrl": "/api/executions/87/stream"
}
```

**Errors:** `404` script not found, `409` max concurrent executions reached, `422` required parameter missing.

**Roles:** `ADMIN`, `TECH`.

---

### GET `/executions`

List execution history.

**Query params:** `scriptId`, `status` (`RUNNING`,`SUCCESS`,`FAILED`,`TIMEOUT`,`CANCELLED`), `triggeredBy` (MANUAL/SCHEDULED), `from`, `to` (ISO-8601 timestamps), pagination.

**Response `200 OK`** — paginated list of execution objects.

**Roles:** `ADMIN`, `TECH`.

---

### GET `/executions/{id}`

Execution detail: status, exit code, duration, who/what triggered it, log summary.

**Response `200 OK`** — execution object (schema §9.2).

**Errors:** `404` not found.

---

### GET `/executions/{id}/log`

Full stdout/stderr log content as `text/plain`. Use `?tail=200` to return only the last N lines, or `?download=true` to get the log file as an attachment.

**Response `200 OK`** — log text.

**Roles:** `ADMIN`, `TECH`.

---

### GET `/executions/{id}/stream`

Live log streaming via **Server-Sent Events (SSE)**. Events:

| Event | Data | Emitted |
|---|---|---|
| `log` | `{ "line": "...", "ts": "...", "stream": "stdout" }` | each new line |
| `status` | `{ "status": "RUNNING", "exitCode": null }` | state changes |
| `complete` | `{ "status": "SUCCESS", "exitCode": 0, "durationMs": 1240 }` | final state |

**Example client:**
```
GET /api/executions/87/stream
Accept: text/event-stream
```

**Roles:** `ADMIN`, `TECH`.

---

### POST `/executions/{id}/cancel`

Request cancellation of a running execution (kills the child process tree).

**Response `202 Accepted`** — execution with `status: "CANCELLING"`.

**Errors:** `409` execution not running.

**Roles:** `ADMIN`, `TECH`.

---

## 6. Scheduled Jobs (Quartz)

### POST `/jobs`

Create a scheduled job.

**Request**
```json
{
  "name": "nightly-backup",
  "description": "Backup /var/www every Sunday 02:00",
  "scriptId": 8,
  "cronExpression": "0 0 2 ? * SUN",
  "arguments": { "dest": "/mnt/nas/backups" },
  "env": {},
  "timeoutSeconds": 900,
  "notifyOn": "ALWAYS",
  "timeZone": "UTC",
  "enabled": true
}
```

**Response `201 Created`** — job object including `status: "SCHEDULED"`.

**Errors:** `400` invalid cron or missing scriptId, `404` script not found.

**Roles:** `ADMIN`.

---

### GET `/jobs`

List scheduled jobs with next fire time (computed from the Quartz trigger).

**Response `200 OK`** — list of job objects (schema §9.4).

**Roles:** `ADMIN`, `TECH`.

---

### GET `/jobs/{id}`

Single job detail including recent execution history.

**Response `200 OK`** — job object.

**Errors:** `404` not found.

---

### PUT `/jobs/{id}`

Update cron, arguments, notify settings, etc. Quartz trigger is re-scheduled atomically.

**Response `200 OK`** — updated job.

**Roles:** `ADMIN`.

---

### DELETE `/jobs/{id}`

Remove the job and its Quartz trigger.

**Response `204 No Content`**

**Errors:** `404` not found.

**Roles:** `ADMIN`.

---

### POST `/jobs/{id}/pause`

Pause scheduling (keeps the job definition; next fires are skipped).

**Response `200 OK`** — job with `status: "PAUSED"`.

**Roles:** `ADMIN`.

---

### POST `/jobs/{id}/resume`

Resume a paused job.

**Response `200 OK`** — job with `status: "SCHEDULED"`.

**Roles:** `ADMIN`.

---

### POST `/jobs/{id}/run-now`

Fire the job immediately regardless of schedule (useful for testing).

**Response `202 Accepted`** — new execution object (`triggeredBy: "SCHEDULED", manualOverride: true`).

**Roles:** `ADMIN`, `TECH`.

---

### GET `/jobs/next-fire-times`

Preview when cron expressions will fire. Useful for the job form UI.

**Request params:** `cron=0+0+2+%3F+*+SUN&timeZone=UTC&count=5`

**Response `200 OK`**
```json
{
  "cron": "0 0 2 ? * SUN",
  "timeZone": "UTC",
  "nextFireTimes": [
    "2026-08-16T02:00:00Z",
    "2026-08-23T02:00:00Z",
    "..."
  ]
}
```

**Roles:** `ADMIN`, `TECH`.

---

## 7. Audit Logs

### GET `/audit`

Query the audit trail.

**Query params:** `userId`, `action` (`SCRIPT_RUN`,`SCRIPT_CREATED`,`SCRIPT_DELETED`,`JOB_CREATED`,`JOB_PAUSED`,`EXECUTION_CANCELLED`,...), `targetType` (`SCRIPT`,`JOB`,`EXECUTION`,`USER`,`AUTH`), `from`, `to`, pagination.

**Response `200 OK`** — paginated audit entries:

```json
{
  "content": [
    {
      "id": 451,
      "actor": { "id": 1, "username": "admin" },
      "action": "SCRIPT_RUN",
      "targetType": "SCRIPT",
      "targetId": "12",
      "details": "execution 87 started for script add_user",
      "ipAddress": "192.168.1.20",
      "timestamp": "2026-08-11T09:15:00Z"
    }
  ],
  "page": 0, "size": 20, "totalElements": 451, "totalPages": 23
}
```

**Roles:** `ADMIN` (all entries); `TECH` (own entries only).

---

### GET `/audit/export`

Download the audit trail as CSV (respects the same visibility rules as `GET /audit`).

**Query params:** same filters as `GET /audit`, plus `format=csv`.

**Response `200 OK`** — `text/csv` attachment.

---

## 8. Notification Settings

### GET `/notifications/settings`

Current email / Slack alert configuration (secrets masked).

**Response `200 OK`**
```json
{
  "email": { "enabled": true, "recipients": ["ops@company.com"] },
  "slack": { "enabled": true, "channel": "#alerts", "webhookUrl": "https://hooks.slack.com/services/***masked***" },
  "defaultNotifyOn": "FAILURE"
}
```

**Roles:** `ADMIN`.

---

### PUT `/notifications/settings`

Update alert configuration. Webhook/SMTP passwords are kept if omitted.

**Request**
```json
{
  "email": { "enabled": true, "recipients": ["ops@company.com", "oncall@company.com"] },
  "slack": { "enabled": true, "channel": "#alerts", "webhookUrl": "https://hooks.slack.com/services/T000/B000/XXXX" },
  "defaultNotifyOn": "ALWAYS"
}
```

**Response `200 OK`** — saved settings (secrets masked).

**Roles:** `ADMIN`.

---

### POST `/notifications/test`

Send a test alert through the configured channels.

**Request**
```json
{ "channel": "all" }
```
`channel`: `email` | `slack` | `all`.

**Response `200 OK`** — delivery report per channel.

**Roles:** `ADMIN`.

---

## 9. Data Schemas

### 9.1 Script
```json
{
  "id": 12,
  "name": "add_user",
  "filename": "add_user.sh",
  "fileType": "SH",
  "description": "Provision a new system user",
  "tags": ["user-provisioning", "identity"],
  "parameters": [{ "name": "username", "label": "Username", "required": true }],
  "sizeBytes": 1420,
  "createdBy": { "id": 1, "username": "admin" },
  "createdAt": "2026-08-11T09:12:00Z",
  "lastExecutedAt": "2026-08-11T09:15:00Z"
}
```

`fileType`: `PY`, `SH`, `PS1`, `BAT`, `CMD`.

### 9.2 Execution
```json
{
  "id": 87,
  "script": { "id": 12, "name": "add_user" },
  "triggeredBy": "MANUAL",
  "triggeredByUser": { "id": 1, "username": "admin" },
  "job": null,
  "status": "SUCCESS",
  "exitCode": 0,
  "startedAt": "2026-08-11T09:15:00Z",
  "finishedAt": "2026-08-11T09:15:01Z",
  "durationMs": 1240,
  "logSizeBytes": 912,
  "arguments": { "username": "mkoss" }
}
```

`status`: `RUNNING`, `SUCCESS`, `FAILED`, `TIMEOUT`, `CANCELLED`.

### 9.3 User
```json
{
  "id": 1,
  "username": "admin",
  "displayName": "System Admin",
  "email": "admin@example.com",
  "role": "ADMIN",
  "enabled": true,
  "lastLoginAt": "2026-08-11T09:14:00Z",
  "createdAt": "2026-07-01T08:00:00Z"
}
```

### 9.4 Job
```json
{
  "id": 5,
  "name": "nightly-backup",
  "description": "Backup /var/www every Sunday 02:00",
  "script": { "id": 8, "name": "backup" },
  "cronExpression": "0 0 2 ? * SUN",
  "timeZone": "UTC",
  "status": "SCHEDULED",
  "nextFireTime": "2026-08-16T02:00:00Z",
  "arguments": { "dest": "/mnt/nas/backups" },
  "notifyOn": "ALWAYS",
  "enabled": true,
  "lastRunAt": "2026-08-09T02:00:00Z",
  "createdBy": { "id": 1, "username": "admin" }
}
```

`status`: `SCHEDULED`, `PAUSED`.

---

## 10. Error Reference

| HTTP | Code | Meaning |
|---|---|---|
| 400 | `VALIDATION_FAILED` | Missing/invalid fields or parameters |
| 400 | `INVALID_CRON` | Malformed cron expression |
| 400 | `CANT_DELETE_SELF` | Admin attempted to delete own account |
| 401 | `UNAUTHORIZED` | Missing/expired/invalid token |
| 403 | `FORBIDDEN` | Authenticated but insufficient role |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Duplicate name, execution already running, etc. |
| 409 | `CONCURRENCY_LIMIT` | Max parallel executions exceeded (default 5) |
| 413 | `FILE_TOO_LARGE` | Upload exceeds 5 MB |
| 422 | `MISSING_PARAMETER` | Required script parameter not supplied |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL` | Server error (details logged server-side) |

---

## 11. End-to-End Workflows

### Workflow A — Login and run a script (curl)

```bash
# 1. Authenticate
curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 2. Store the token
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r .accessToken)

# 3. Upload a script
curl -s -X POST http://localhost:8080/api/scripts \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@backup.sh" \
  -F "name=backup" \
  -F "tags=backup" \
  -F 'parameters=[{"name":"dest","label":"Destination","required":true}]'

# 4. Run it on demand
curl -s -X POST http://localhost:8080/api/scripts/8/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"arguments":{"dest":"/mnt/nas/backups"},"notifyOn":"FAILURE"}'

# 5. Tail the live log
curl -s -N http://localhost:8080/api/executions/87/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: text/event-stream"
```

### Workflow B — Schedule a weekly job

```bash
TOKEN=$(...jq -r .accessToken)

curl -s -X POST http://localhost:8080/api/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sunday-backup",
    "scriptId": 8,
    "cronExpression": "0 0 2 ? * SUN",
    "arguments": { "dest": "/mnt/nas/backups" },
    "notifyOn": "ALWAYS",
    "timeZone": "UTC"
  }'
```

### Workflow C — Browser demo (recruiter script)

1. Log in as `admin` / `admin123` (UI) — or `tech` / `tech123`.
2. Dashboard shows live stats: scripts, jobs, executions, success rate.
3. **Script Library** → upload `add_user.sh` → **Run** with `username=jdoe` → watch the
   log stream line-by-line, see `SUCCESS` + exit code `0`.
4. **Scheduler** → create `daily-patch` at `0 3 * * *` → **Pause** → **Run Now**.
5. **Audit** tab shows every action with actor, IP, timestamp.
6. Delete a script as `admin`; log in as `tech` and confirm you **cannot** delete it (`403`).

---

## 12. Roadmap: v2 Server Agents

The next major version introduces a lightweight Java agent that runs on remote
servers, enabling distributed execution:

| Endpoint (agent) | Method | Description |
|---|---|---|
| `POST /api/agents/register` | Agent → Server | Register agent (hostname, OS, token) |
| `POST /api/agents/{id}/heartbeat` | Agent → Server | Health check every 30 s |
| `POST /api/agents/{id}/execute` | Server → Agent | Dispatch a script for remote execution |
| `POST /api/agents/{id}/result` | Agent → Server | Push exit code + log chunks back |

Corresponding server-side additions: `POST /executions` gains a `targetAgent` field,
and a new `GET /agents` admin endpoint lists registered servers with last-seen status.

---

*Generated for the AutoRun project. Subject to change as the codebase evolves.*
