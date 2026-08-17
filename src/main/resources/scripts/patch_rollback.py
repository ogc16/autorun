#!/usr/bin/env python3
"""
Patch Rollback Script
Automates reverting to previous package versions when a patch fails.
Supports pip, apt/dpkg, yum/dnf, and npm.

Parameters:
  manager    : Package manager to use (required: pip, apt, yum, npm)
  package    : Package name to rollback (required)
  version    : Target version to rollback to (required for pip/npm)
  dry_run    : Only show what would be done (default: true)
  snapshot   : Path to a version snapshot file (alternative to specifying version)
"""
import json
import subprocess
import sys
from datetime import datetime


def run_cmd(cmd, timeout=120):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except FileNotFoundError:
        return None, "Command not found", -1
    except subprocess.TimeoutExpired:
        return None, "Command timed out", -2


def rollback_pip(package, version, dry_run):
    result = {"manager": "pip", "package": package, "target_version": version,
              "action": "rollback", "success": False, "error": None}

    if dry_run:
        result["dry_run"] = True
        result["command"] = f"pip install {package}=={version}"
        return result

    out, err, rc = run_cmd([sys.executable, "-m", "pip", "install", f"{package}=={version}"])
    if rc == 0:
        result["success"] = True
        result["output"] = out
    else:
        result["error"] = err or out
    return result


def rollback_apt(package, version, dry_run):
    result = {"manager": "apt", "package": package, "target_version": version,
              "action": "rollback", "success": False, "error": None}

    if dry_run:
        result["dry_run"] = True
        result["command"] = f"apt-get install -y {package}={version}" if version else f"apt-get install --reinstall -y {package}"
        return result

    if version:
        out, err, rc = run_cmd(["apt-get", "install", "-y", f"{package}={version}"])
    else:
        out, err, rc = run_cmd(["apt-get", "install", "--reinstall", "-y", package])

    if rc == 0:
        result["success"] = True
        result["output"] = out
    else:
        result["error"] = err or out
    return result


def rollback_yum(package, version, dry_run):
    result = {"manager": "yum", "package": package, "target_version": version,
              "action": "rollback", "success": False, "error": None}

    pkg_mgr = "dnf" if subprocess.run(["which", "dnf"], capture_output=True).returncode == 0 else "yum"

    if dry_run:
        result["dry_run"] = True
        result["command"] = f"{pkg_mgr} history undo last"
        return result

    if version:
        out, err, rc = run_cmd([pkg_mgr, "downgrade", "-y", f"{package}-{version}"])
    else:
        out, err, rc = run_cmd([pkg_mgr, "history", "undo", "last", "-y"])

    if rc == 0:
        result["success"] = True
        result["output"] = out
    else:
        result["error"] = err or out
    return result


def rollback_npm(package, version, dry_run):
    result = {"manager": "npm", "package": package, "target_version": version,
              "action": "rollback", "success": False, "error": None}

    if dry_run:
        result["dry_run"] = True
        result["command"] = f"npm install -g {package}@{version}" if version else f"npm install -g {package}"
        return result

    pkg_spec = f"{package}@{version}" if version else package
    out, err, rc = run_cmd(["npm", "install", "-g", pkg_spec])

    if rc == 0:
        result["success"] = True
        result["output"] = out
    else:
        result["error"] = err or out
    return result


def load_snapshot(snapshot_path):
    try:
        with open(snapshot_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"Failed to load snapshot: {e}"}))
        sys.exit(1)


def main():
    manager = ""
    package = ""
    version = ""
    dry_run = True
    snapshot_path = ""

    for arg in sys.argv[1:]:
        if arg.startswith("manager="):
            manager = arg.split("=", 1)[1]
        elif arg.startswith("package="):
            package = arg.split("=", 1)[1]
        elif arg.startswith("version="):
            version = arg.split("=", 1)[1]
        elif arg.startswith("dry_run="):
            dry_run = arg.split("=", 1)[1].lower() == "true"
        elif arg.startswith("snapshot="):
            snapshot_path = arg.split("=", 1)[1]

    if snapshot_path:
        snapshot = load_snapshot(snapshot_path)
        manager = snapshot.get("manager", manager)
        package = snapshot.get("package", package)
        version = snapshot.get("version", version)

    if not manager or not package:
        print(json.dumps({"error": "manager and package parameters are required"}))
        sys.exit(1)

    ROLLBACKERS = {
        "pip": rollback_pip,
        "apt": rollback_apt,
        "yum": rollback_yum,
        "dnf": rollback_yum,
        "npm": rollback_npm,
    }

    if manager not in ROLLBACKERS:
        print(json.dumps({"error": f"Unsupported manager: {manager}. Supported: {list(ROLLBACKERS.keys())}"}))
        sys.exit(1)

    result = ROLLBACKERS[manager](package, version, dry_run)
    result["timestamp"] = datetime.utcnow().isoformat() + "Z"

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") or dry_run else 1)


if __name__ == "__main__":
    main()
