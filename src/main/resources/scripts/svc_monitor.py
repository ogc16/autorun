#!/usr/bin/env python3
"""
Service Monitor Script
Checks status of system services and optionally restarts failed ones.
Cross-platform (Linux systemd, Windows services).

Parameters:
  services  : Comma-separated service names to monitor (required)
  auto_restart : Automatically restart failed services (default: false)
  timeout   : Timeout for status check in seconds (default: 10)
"""
import json
import platform
import subprocess
import sys
from datetime import datetime


def run_cmd(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception:
        return None, -1


def check_linux_service(name, auto_restart=False, timeout=10):
    result = {"name": name, "platform": "linux", "active": False,
              "status": "unknown", "sub_state": None, "error": None, "restarted": False}

    out, rc = run_cmd(["systemctl", "is-active", name], timeout=timeout)
    result["active"] = rc == 0 and out == "active"
    result["status"] = out if out else "not-found"

    out, rc = run_cmd(["systemctl", "show", name, "--property=ActiveState,SubState,ExecMainStartTimestamp"],
                       timeout=timeout)
    if rc == 0 and out:
        for line in out.splitlines():
            if line.startswith("SubState="):
                result["sub_state"] = line.split("=", 1)[1]
            if line.startswith("ExecMainStartTimestamp="):
                result["started_at"] = line.split("=", 1)[1]

    if not result["active"] and auto_restart:
        restart_out, restart_rc = run_cmd(["systemctl", "restart", name], timeout=timeout * 3)
        if restart_rc == 0:
            result["restarted"] = True
            result["status"] = "active (restarted)"
            result["active"] = True
        else:
            result["error"] = f"Restart failed: {restart_out}"

    return result


def check_windows_service(name, auto_restart=False, timeout=10):
    result = {"name": name, "platform": "windows", "active": False,
              "status": "unknown", "error": None, "restarted": False}

    out, rc = run_cmd(["powershell", "-NoProfile", "-Command",
                       f"(Get-Service -Name '{name}' -ErrorAction SilentlyContinue).Status"],
                       timeout=timeout)
    if rc != 0 or not out:
        result["status"] = "not-found"
        return result

    result["status"] = out
    result["active"] = out == "Running"

    if not result["active"] and auto_restart:
        restart_out, restart_rc = run_cmd(
            ["powershell", "-NoProfile", "-Command",
             f"Start-Service -Name '{name}' -ErrorAction Stop"],
            timeout=timeout * 3
        )
        if restart_rc == 0:
            result["restarted"] = True
            result["status"] = "Running (restarted)"
            result["active"] = True
        else:
            result["error"] = f"Restart failed: {restart_out}"

    return result


def main():
    services_raw = ""
    auto_restart = False
    timeout = 10

    for arg in sys.argv[1:]:
        if arg.startswith("services="):
            services_raw = arg.split("=", 1)[1]
        elif arg.startswith("auto_restart="):
            auto_restart = arg.split("=", 1)[1].lower() == "true"
        elif arg.startswith("timeout="):
            timeout = int(arg.split("=", 1)[1])

    if not services_raw:
        print(json.dumps({"error": "services parameter is required"}))
        sys.exit(1)

    services = [s.strip() for s in services_raw.split(",") if s.strip()]
    is_linux = platform.system() != "Windows"

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "platform": platform.system().lower(),
        "auto_restart": auto_restart,
        "results": [],
        "summary": {"total": len(services), "active": 0, "inactive": 0, "restarted": 0, "errors": []}
    }

    for svc in services:
        if is_linux:
            check = check_linux_service(svc, auto_restart, timeout)
        else:
            check = check_windows_service(svc, auto_restart, timeout)

        report["results"].append(check)

        if check["active"]:
            report["summary"]["active"] += 1
        else:
            report["summary"]["inactive"] += 1
        if check["restarted"]:
            report["summary"]["restarted"] += 1
        if check["error"]:
            report["summary"]["errors"].append({"service": svc, "error": check["error"]})

    report["status"] = "OK" if report["summary"]["inactive"] == 0 else "DEGRADED"

    print(json.dumps(report, indent=2))
    sys.exit(0 if report["summary"]["inactive"] == 0 else 1)


if __name__ == "__main__":
    main()
