# AutoRun — User Guide

Everything you need to actually use AutoRun, from first login to scheduled jobs and alerts.

---

## 1. First Login

Open the app and sign in:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Tech | `tech` | `tech123` |

> The accounts are seeded automatically on first start. **Change the admin password right away**
> (Settings → Users is planned; for now update via SQL or env-based seed) in any shared environment.

### What's on the dashboard

- **Stat cards** — number of scripts, scheduled jobs, total executions, and success rate.
- **Recent executions** — click any row to open its live/archived log.
- **Status breakdown** — success / failed / timeout / cancelled / running at a glance.

---

## 2. Roles & Permissions

| Action | Admin | Tech |
|---|---|---|
| Browse everything | ✅ | ✅ |
| Upload / edit scripts | ✅ | ✅ |
| Run scripts on demand | ✅ | ✅ |
| Cancel a running execution | ✅ | ✅ |
| Schedule / edit / pause / resume / delete jobs | ✅ | ✅ |
| **Delete scripts** | ✅ | ❌ |
| Manage users | ✅ | ❌ |
| Configure email / Slack alerts | ✅ | ❌ |
| Audit trail | all entries | own entries only |

The UI hides actions you can't perform (e.g. Tech never sees the **Delete** button on a script), and
the server enforces the same rules on the REST API.

---

## 3. Script Library

### Uploading a script

1. **Scripts → Upload Script**.
2. Fill in:
   - **Name** — unique, e.g. `nightly-backup`.
   - **Description** — what it does.
   - **Tags** — comma-separated (`backup, linux, prod`).
   - **Parameters (JSON)** — optional declaration of CLI arguments. Example:
     ```json
     [
       { "name": "src", "label": "Source dir", "required": true },
       { "name": "dest", "label": "Destination", "required": false, "defaultValue": "./backups" }
     ]
     ```
     Supported fields: `name`, `label`, `description`, `required`, `defaultValue`.
   - **File** — `.sh`, `.py`, `.ps1`, `.bat`, `.cmd` (max 5 MB).
3. Save. The script now has its own page with a **Run** form and source preview.

### Editing

Open the script → **Edit** → change metadata / parameters, optionally replace the file
(must stay the same type).

### Deleting (Admin only)

Admin sees a **Delete** button. A script referenced by scheduled jobs cannot be deleted until
those jobs are removed first — this prevents silently breaking schedules.

---

## 4. Running Scripts

### On demand

1. Open the script page.
2. Fill the parameter inputs (rendered from the script's declared parameters).
3. Optionally add **extra raw arguments** (e.g. `--verbose`).
4. Choose **Notify on**: `Failure only` (default), `Always`, or `Never`.
5. Click **Run Script** — you're taken straight to the live log.

### The live log page

- stdout / stderr stream in **real time** (SSE). stderr lines are tinted red.
- Status badge updates live; **exit code**, **duration**, start/finish times shown.
- **Download log** — full plain-text copy of the run.
- **Cancel** — kills a running script (available while `RUNNING`).

### What the statuses mean

| Status | Meaning |
|---|---|
| `RUNNING` | process is active |
| `SUCCESS` | exited with code 0 |
| `FAILED` | exited non-zero, or couldn't be launched |
| `TIMEOUT` | killed after the configured timeout (default 10 min) |
| `CANCELLED` | stopped by a user |

---

## 5. Scheduling Jobs

1. **Scheduler → New Job**.
2. Name it, pick a script, enter a **cron expression** (Quartz 6-field format), and click
   **Preview** to see the next 5 fire times.
3. Optional: fixed **arguments (JSON)** passed on every run, plus the alert policy.
4. Save.

| Button | Effect |
|---|---|
| ▶ Run now | fire immediately, regardless of schedule |
| ⏸ / ▶ pause-resume | stop/start future fires (definition kept) |
| ✏ Edit | change cron, script, arguments |
| 🗑 Delete | remove job and its trigger |

Each scheduled run appears under **Executions** with `triggered by: SCHEDULED` — and it's audited
the same as a manual run.

### Cron cheat-sheet

```
0 0 2 ? * SUN     Sundays 02:00
0 3 * * *         every day 03:00
0 */30 * * * ?    every 30 minutes
0 0 22 ? * MON-FRI  weekdays 22:00
```

---

## 6. Alerts

**Alerts** (Admin only) configures delivery:

- **Slack** — enable + paste an incoming webhook URL (optional channel, e.g. `#alerts`).
- **Email** — enable + recipient list. Requires SMTP to be configured at deployment time
  (`AUTORUN_SMTP_HOST`, `AUTORUN_SMTP_USERNAME`, `AUTORUN_SMTP_PASSWORD`).

Click **Send test alert** to verify delivery.

Alerts are per-run: the **Notify on** selector on the Run form and on each job decides whether
that run notifies on failure, always, or never.

---

## 7. Audit Trail

**Audit** shows every action: logins, script uploads/updates/deletes, executions, cancellations,
job changes — with **who**, **what**, **when**, and **which IP**.

- Admins see the full trail.
- Tech users see only their own actions.
- **Export CSV** downloads the current view for compliance records.

---

## 8. Using the REST API

Authenticate once, reuse the token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r .accessToken)
```

| Task | Example |
|---|---|
| List scripts | `curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/scripts` |
| Run a script | `curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"arguments":{"days":"3"}}' http://localhost:8080/api/scripts/1/execute` |
| Tail live log | `curl -N -H "Authorization: Bearer $TOKEN" -H "Accept: text/event-stream" http://localhost:8080/api/executions/1/stream` |
| Schedule a job | `curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"daily-backup","scriptId":3,"cronExpression":"0 3 * * *","notifyOn":"FAILURE"}' http://localhost:8080/api/jobs` |
| Export audit | `curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/audit/export -o audit.csv` |

Full endpoint reference: [`docs/API.md`](API.md).

---

## 9. Sample Scripts (seeded)

| Script | Interpreter | What it shows |
|---|---|---|
| `system_info` | CMD | runs anywhere; the "hello world" of AutoRun |
| `collect_logs` | Python | parameter (`days`), cross-platform file scan |
| `backup` | Bash | two required parameters, produces a `.tar.gz` |
| `patch_apt` | Bash | the classic patching use-case (needs root) |
| `add_user` | Bash | user-provisioning use-case (needs root) |

The Bash scripts are designed for the **Docker / Linux** deployment; use `system_info` or
`collect_logs` for a quick local demo on Windows.
