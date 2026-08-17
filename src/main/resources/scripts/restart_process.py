#!/usr/bin/env python3
"""
Process Restart Helper
Finds and restarts a process by name using systemctl (Linux) or taskkill/sc (Windows).

Parameters:
  process_name : Name of the process/service to restart (required)
  method       : Restart method: 'systemctl', 'kill', or 'taskkill' (default: auto-detect)
  signal       : Signal to send when using kill method (default: SIGTERM)
  wait_seconds : Seconds to wait after kill before checking (default: 5)
"""
import json
import os
import platform
import subprocess
import sys
import time


def detect_os():
    if platform.system() == "Windows":
        return "windows"
    return "linux"


def find_pids_linux(name: str) -> list:
    try:
        out = subprocess.check_output(["pgrep", "-f", name], text=True, stderr=subprocess.DEVNULL).strip()
        return [int(pid) for pid in out.splitlines() if pid.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def find_pids_windows(name: str) -> list:
    try:
        out = subprocess.check_output(
            ["powershell", "-Command",
             f"Get-Process -Name '{name}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        return [int(pid) for pid in out.splitlines() if pid.strip()]
    except Exception:
        return []


def restart_systemctl(service_name: str) -> dict:
    result = {"method": "systemctl", "service": service_name, "success": False, "error": None}
    try:
        subprocess.run(["systemctl", "restart", service_name], check=True, capture_output=True, text=True)
        result["success"] = True
    except FileNotFoundError:
        result["error"] = "systemctl not found"
    except subprocess.CalledProcessError as e:
        result["error"] = e.stderr.strip() or f"systemctl restart failed with code {e.returncode}"
    return result


def restart_kill(name: str, signal_name: str, wait: int) -> dict:
    os_name = detect_os()
    pids = find_pids_windows(name) if os_name == "windows" else find_pids_linux(name)
    result = {"method": "kill", "process": name, "pids_found": len(pids), "killed": 0, "success": False, "error": None}
    if not pids:
        result["error"] = f"No running process found matching '{name}'"
        return result
    for pid in pids:
        try:
            if os_name == "windows":
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True, capture_output=True, text=True)
            else:
                os.kill(pid, getattr(__import__("signal"), signal_name.replace("SIG", "SIG"), signal.SIGTERM))
            result["killed"] += 1
        except Exception as e:
            result["error"] = str(e)
    if wait > 0 and result["killed"] > 0:
        time.sleep(wait)
    result["success"] = result["killed"] > 0
    return result


def restart_taskkill(name: str) -> dict:
    result = {"method": "taskkill", "process": name, "success": False, "error": None}
    try:
        subprocess.run(["taskkill", "/IM", name, "/F"], check=True, capture_output=True, text=True)
        result["success"] = True
    except FileNotFoundError:
        result["error"] = "taskkill not found (not Windows?)"
    except subprocess.CalledProcessError as e:
        result["error"] = e.stderr.strip() or f"taskkill failed with code {e.returncode}"
    return result


def main():
    process_name = ""
    method = "auto"
    signal_name = "SIGTERM"
    wait_seconds = 5

    for arg in sys.argv[1:]:
        if arg.startswith("process_name="):
            process_name = arg.split("=", 1)[1]
        elif arg.startswith("method="):
            method = arg.split("=", 1)[1]
        elif arg.startswith("signal="):
            signal_name = arg.split("=", 1)[1]
        elif arg.startswith("wait_seconds="):
            try:
                wait_seconds = int(arg.split("=", 1)[1])
            except ValueError:
                pass

    if not process_name:
        print("ERROR: process_name parameter is required")
        sys.exit(1)

    os_name = detect_os()

    if method == "auto":
        if os_name == "windows":
            method = "taskkill"
        else:
            systemctl_available = subprocess.run(
                ["which", "systemctl"], capture_output=True, stderr=subprocess.DEVNULL
            ).returncode == 0
            method = "systemctl" if systemctl_available else "kill"

    if method == "systemctl":
        result = restart_systemctl(process_name)
    elif method == "taskkill":
        result = restart_taskkill(process_name)
    else:
        result = restart_kill(process_name, signal_name, wait_seconds)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
