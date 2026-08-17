#!/usr/bin/env python3
"""
Third-Party Patch Script
Checks for updates to third-party packages: pip, npm, Docker, Java, and more.

Parameters:
  managers  : Comma-separated list of managers to check (default: all available)
              Options: pip, npm, docker, java, dotnet
  dry_run   : Only check, do not install (default: true)
  upgrade   : Actually install upgrades (default: false)
"""
import json
import subprocess
import sys
from datetime import datetime


def run_cmd(cmd, timeout=60):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    except FileNotFoundError:
        return None, -1
    except subprocess.TimeoutExpired:
        return None, -2


def check_pip():
    result = {"manager": "pip", "available": False, "current_version": None,
              "packages": [], "upgradable": [], "error": None}

    out, rc = run_cmd([sys.executable, "-m", "pip", "--version"])
    if rc != 0 or not out:
        result["error"] = "pip not found"
        return result

    result["available"] = True
    result["current_version"] = out.split()[1] if len(out.split()) > 1 else "unknown"

    out, rc = run_cmd([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if rc == 0 and out:
        try:
            outdated = json.loads(out)
            for pkg in outdated:
                result["upgradable"].append({
                    "name": pkg["name"],
                    "installed": pkg["version"],
                    "latest": pkg["latest_version"]
                })
                result["packages"].append(pkg["name"])
        except json.JSONDecodeError:
            result["error"] = "Failed to parse pip output"
    return result


def upgrade_pip():
    log = {"manager": "pip", "action": "upgrade", "upgraded": [], "failed": [], "error": None}

    out, rc = run_cmd([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if rc != 0 or not out:
        return log

    try:
        outdated = json.loads(out)
        for pkg in outdated:
            name = pkg["name"]
            _, rc = run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", name])
            if rc == 0:
                log["upgraded"].append(name)
            else:
                log["failed"].append(name)
    except json.JSONDecodeError:
        log["error"] = "Failed to parse pip output"
    return log


def check_npm():
    result = {"manager": "npm", "available": False, "current_version": None,
              "packages": [], "upgradable": [], "error": None}

    out, rc = run_cmd(["npm", "--version"])
    if rc != 0:
        result["error"] = "npm not found"
        return result

    result["available"] = True
    result["current_version"] = out

    out, rc = run_cmd(["npm", "outdated", "--json"], timeout=120)
    if rc == 0 and out:
        try:
            outdated = json.loads(out)
            for name, info in outdated.items():
                result["upgradable"].append({
                    "name": name,
                    "installed": info.get("current", "unknown"),
                    "latest": info.get("latest", "unknown")
                })
                result["packages"].append(name)
        except json.JSONDecodeError:
            pass
    return result


def upgrade_npm():
    log = {"manager": "npm", "action": "upgrade", "upgraded": [], "failed": [], "error": None}

    out, rc = run_cmd(["npm", "outdated", "--json"], timeout=120)
    if rc == 0 and out:
        try:
            outdated = json.loads(out)
            for name in outdated.keys():
                _, rc = run_cmd(["npm", "install", "-g", name])
                if rc == 0:
                    log["upgraded"].append(name)
                else:
                    log["failed"].append(name)
        except json.JSONDecodeError:
            pass
    return log


def check_docker():
    result = {"manager": "docker", "available": False, "current_version": None,
              "packages": [], "upgradable": [], "error": None}

    out, rc = run_cmd(["docker", "--version"])
    if rc != 0:
        result["error"] = "docker not found"
        return result

    result["available"] = True
    result["current_version"] = out.split()[-1].rstrip(",") if out else "unknown"

    out, rc = run_cmd(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.Size}}"], timeout=30)
    if rc == 0 and out:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 1 and parts[0] != "<none>:<none>":
                result["packages"].append(parts[0])

    return result


def check_java():
    result = {"manager": "java", "available": False, "current_version": None,
              "packages": [], "upgradable": [], "error": None}

    out, rc = run_cmd(["java", "-version"], timeout=10)
    if rc != 0:
        result["error"] = "java not found"
        return result

    result["available"] = True
    result["current_version"] = out.splitlines()[0].strip() if out else "unknown"

    return result


def main():
    managers_raw = "all"
    dry_run = True

    for arg in sys.argv[1:]:
        if arg.startswith("managers="):
            managers_raw = arg.split("=", 1)[1]
        elif arg.startswith("dry_run="):
            dry_run = arg.split("=", 1)[1].lower() == "true"
        elif arg.startswith("upgrade="):
            if arg.split("=", 1)[1].lower() == "true":
                dry_run = False

    CHECKERS = {
        "pip": check_pip,
        "npm": check_npm,
        "docker": check_docker,
        "java": check_java,
    }

    UPGRADES = {
        "pip": upgrade_pip,
        "npm": upgrade_npm,
    }

    if managers_raw == "all":
        managers = list(CHECKERS.keys())
    else:
        managers = [m.strip() for m in managers_raw.split(",")]

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dry_run": dry_run,
        "managers_checked": [],
        "summary": {"total_upgradable": 0, "managers_with_updates": 0}
    }

    for mgr in managers:
        if mgr not in CHECKERS:
            report["managers_checked"].append({"manager": mgr, "error": f"Unknown manager: {mgr}"})
            continue

        check_result = CHECKERS[mgr]()
        report["managers_checked"].append(check_result)

        if check_result["upgradable"]:
            report["summary"]["total_upgradable"] += len(check_result["upgradable"])
            report["summary"]["managers_with_updates"] += 1

    if not dry_run:
        report["upgrade_results"] = []
        for mgr in managers:
            if mgr in UPGRADES and any(
                c["manager"] == mgr and c.get("upgradable")
                for c in report["managers_checked"]
            ):
                upgrade_result = UPGRADES[mgr]()
                report["upgrade_results"].append(upgrade_result)

    print(json.dumps(report, indent=2))
    sys.exit(0 if report["summary"]["total_upgradable"] == 0 or not dry_run else 1)


if __name__ == "__main__":
    main()
