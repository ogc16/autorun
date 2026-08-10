# AutoRun — Deployment Guide

How to run AutoRun in production-like environments: Docker, MySQL, environment variables, and
hardening.

---

## 1. Quick Reference

| Component | Tech |
|---|---|
| App runtime | Java 17 (target), Spring Boot 3.3 |
| Database | MySQL 8 (recommended) or H2 (local dev only) |
| Build | Maven / `./mvnw` |
| Container | Multi-stage `Dockerfile` → non-root JRE image |

---

## 2. Prerequisites

- **Java 17+** (any LTS: 17 / 21) and Maven 3.9+, **or** just Docker.
- MySQL 8 server (if not using Compose).

---

## 3. Option A — Run from JAR (dev / demo)

```bash
mvn -DskipTests package
java -jar target/autorun-1.0.0.jar
```

Opens on `http://localhost:8080` using an **H2 file database** in `./data`.
Seeded accounts: `admin/admin123`, `tech/tech123`.

To use MySQL instead, set the profile and env vars:

```bash
set AUTORUN_DB_HOST=localhost
set AUTORUN_DB_PORT=3306
set AUTORUN_DB_NAME=autorun
set AUTORUN_DB_USER=autorun
set AUTORUN_DB_PASSWORD=change-me
set AUTORUN_JWT_SECRET=<64+ char random string>
java -jar target/autorun-1.0.0.jar --spring.profiles.active=mysql
```

> `createDatabaseIfNotExist=true` creates the database on first connect if it is missing.

---

## 4. Option B — Docker Compose (recommended)

```bash
docker compose up --build -d
```

| Service | Port | Notes |
|---|---|---|
| `autorun-db` | 3306 (internal) | MySQL 8, volume-backed, healthcheck |
| `autorun` | 8080 → host | JRE 21, runs as `autorun` (non-root), `/autorun/data` volume |

The demo `docker-compose.yml` uses fixed, weak credentials for local development — **change the
DB password and JWT secret before exposing it anywhere**. Either edit the inline `environment`
values or load them from a git-ignored `.env`:

```bash
# .env (git-ignored)
AUTORUN_DB_PASSWORD=strong-db-password
AUTORUN_JWT_SECRET=<64+ char random string>
```

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SPRING_PROFILES_ACTIVE` | `mysql` | Enables MySQL datasource + DDL |
| `AUTORUN_DB_HOST` / `AUTORUN_DB_PORT` | `localhost` / `3306` | MySQL host and port |
| `AUTORUN_DB_NAME` | `autorun` | Database name (auto-created if missing) |
| `AUTORUN_DB_USER` / `AUTORUN_DB_PASSWORD` | `autorun` / `autorun` | DB credentials |
| `AUTORUN_JWT_SECRET` | demo default | HMAC key for access tokens (**required** in prod) |
| `AUTORUN_MAIL_ENABLED` | `false` | SMTP on/off |
| `AUTORUN_SMTP_HOST` / `AUTORUN_SMTP_PORT` | — | SMTP server |
| `AUTORUN_SMTP_USERNAME` / `AUTORUN_SMTP_PASSWORD` | — | SMTP auth |
| `AUTORUN_SMTP_FROM` | `autorun@localhost` | Sender address |
| `AUTORUN_PYTHON_INTERPRETER` | `python` | Interpreter for `.py` scripts |
| `AUTORUN_MAX_CONCURRENT` | `5` | Concurrent-execution cap |
| `AUTORUN_TIMEOUT_SECONDS` | `600` | Per-run hard timeout |
| `AUTORUN_STORAGE_DIR` | `./data/scripts` | Script file storage |
| `AUTORUN_LOG_DIR` | `./data/logs` | Execution log files |
| `SERVER_PORT` | `8080` | HTTP port |
| `JAVA_OPTS` | — | JVM flags, e.g. `-Xmx512m` |

---

## 5. Option C — Cloud Run / K8s (sketch)

The image is a standard, non-root Spring Boot container, so it runs anywhere that runs containers:

```bash
docker build -t gcr.io/<project>/autorun:1.0.0 .
docker push gcr.io/<project>/autorun:1.0.0
# deploy with env vars above + a managed MySQL / Cloud SQL
```

Notes for managed platforms:

- Point `AUTORUN_DB_URL` at a managed MySQL (enable SSL in the JDBC URL if the platform requires it).
- Mount `AUTORUN_STORAGE_DIR` / `AUTORUN_LOG_DIR` on persistent storage; ephemeral disks lose scripts and log files on restart.
- Consider a **JDBC-backed Quartz job store** for HA (2+ replicas) so cron triggers survive restarts:
  replace the in-memory job store with `org.quartz.impl.jdbcjobstore.JobStoreTX`.
- Use a secret manager for `AUTORUN_JWT_SECRET`, DB and SMTP credentials.

---

## 6. Security Hardening Checklist

- [ ] Change `admin` / `tech` seeded passwords immediately.
- [ ] Set a strong `AUTORUN_JWT_SECRET` (≥ 32 random bytes, base64) — never the demo default.
- [ ] Run behind TLS (reverse proxy or platform-managed certs).
- [ ] Keep the container **non-root** (the provided `Dockerfile` already does this).
- [ ] Bind the port to a trusted network; scripts run with the app's privileges, so isolate the
      host (dedicated VM / namespace).
- [ ] Put MySQL on a private network, not exposed to the internet.
- [ ] Enforce firewall rules; consider restricting the admin UI by IP if needed.
- [ ] Configure SMTP with TLS; never log credentials.
- [ ] Review `data/logs` retention; script output may contain sensitive data.
- [ ] Pin image digests and dependabot-update base images in CI.

---

## 7. Operations

### Health checks

- `GET /actuator/health` — container-ready signal.
- Compose defines a healthcheck that waits for MySQL before the app starts.

### Logs

- App logs → stdout (container) or `logs/` (local).
- Script output → `data/logs/execution-<id>.log` + the `execution_logs.log_content` column.

### Backup

Back up the database **and** `AUTORUN_STORAGE_DIR` / `AUTORUN_LOG_DIR` together — scripts and log files live on disk,
execution history in the DB.

### Upgrades

1. Pull new image / jar.
2. `docker compose pull && docker compose up -d` (volume-backed data survives).
3. Verify `/actuator/health` and run a smoke script.

---

## 8. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `Access denied for user` | Wrong `AUTORUN_DB_*`; recreate DB user with the right grants |
| Scripts exit instantly with `TIMEOUT` | Interpreter missing — set `AUTORUN_PYTHON_INTERPRETER` / install bash/PowerShell on the host |
| `.sh` fails on Windows host | `bash` isn't available on Windows; run the Linux sample scripts via Docker |
| `Connection refused` at startup | MySQL not ready; Compose healthcheck handles this — for manual runs wait for MySQL first |
| 401 on `/api/**` but UI works | Expired/absent `accessToken`; call `/api/auth/refresh` |
| Emails not sent | `AUTORUN_MAIL_ENABLED=true` + valid `AUTORUN_SMTP_*`; check app logs for SMTP errors |

---

## 9. CI/CD

`.github/workflows/ci.yml` builds the project and runs tests on every push/PR to `main`. The release
pipeline is intentionally minimal — extend it with:

```yaml
# push the image when a tag v* is created
on: push: { tags: ["v*"] }
```

…or wire a deployment step to Cloud Run / your favourite platform using the Dockerfile.
