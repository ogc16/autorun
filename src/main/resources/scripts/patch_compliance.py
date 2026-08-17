#!/usr/bin/env python3
"""
Patch Compliance Report Generator
Generates daily/weekly patch compliance reports for stakeholders.
Combines inventory, patch status, and verification data into
a single structured report suitable for audit and compliance.

Parameters:
  period     : Report period: daily, weekly (default: daily)
  output     : Output format: json, table, csv (default: json)
  include_fixes : Include recommended fixes (default: true)
"""
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timedelta


def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, -1


def get_os_patch_status():
    status = {"os": platform.system(), "pending_updates": 0, "last_update_check": None,
              "security_updates": 0, "error": None}

    if platform.system() == "Linux":
        if os.path.exists("/usr/bin/apt"):
            out, rc = run_cmd(["apt", "list", "--upgradable"])
            if rc == 0 and out:
                lines = [l for l in out.splitlines() if "upgradable" in l]
                status["pending_updates"] = len(lines)
                status["security_updates"] = len([l for l in lines if "security" in l.lower()])
        elif os.path.exists("/usr/bin/yum"):
            out, rc = run_cmd(["yum", "check-update"])
            if rc == 100 and out:
                status["pending_updates"] = len([l for l in out.splitlines() if l.strip()])

    elif platform.system() == "Windows":
        out, rc = run_cmd(["powershell", "-NoProfile", "-Command",
                           "Import-Module PSWindowsUpdate -ErrorAction SilentlyContinue; "
                           "$u = Get-WindowsUpdate -ErrorAction SilentlyContinue; "
                           "if ($u) { $u.Count } else { 0 }"])
        if rc == 0 and out and out.isdigit():
            status["pending_updates"] = int(out)

    return status


def get_pip_compliance():
    result = {"packages": [], "total": 0, "upgradable": 0, "error": None}

    out, rc = run_cmd([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if rc != 0:
        result["error"] = "pip not available"
        return result

    try:
        outdated = json.loads(out)
        result["total"] = len(outdated)
        result["upgradable"] = len(outdated)
        for pkg in outdated:
            result["packages"].append({
                "name": pkg["name"],
                "installed": pkg["version"],
                "latest": pkg["latest_version"]
            })
    except json.JSONDecodeError:
        pass

    return result


def get_npm_compliance():
    result = {"packages": [], "total": 0, "upgradable": 0, "error": None}

    out, rc = run_cmd(["npm", "outdated", "--json"], timeout=120)
    if rc != 0 or not out:
        result["error"] = "npm not available or no packages"
        return result

    try:
        outdated = json.loads(out)
        for name, info in outdated.items():
            result["packages"].append({
                "name": name,
                "installed": info.get("current", "unknown"),
                "latest": info.get("latest", "unknown")
            })
        result["total"] = len(outdated)
        result["upgradable"] = len(outdated)
    except json.JSONDecodeError:
        pass

    return result


def get_docker_compliance():
    result = {"images": [], "total_images": 0, "error": None}

    out, rc = run_cmd(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.CreatedSince}}"])
    if rc != 0:
        result["error"] = "docker not available"
        return result

    if out:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0] != "<none>:<none>":
                result["images"].append({"image": parts[0], "created": parts[1]})
        result["total_images"] = len(result["images"])

    return result


def calculate_compliance_score(patch_status, pip_comp, npm_comp, docker_comp):
    total = 0
    compliant = 0

    # OS patches
    total += 1
    if patch_status["pending_updates"] == 0:
        compliant += 1

    # Pip packages
    total += 1
    if pip_comp["upgradable"] == 0:
        compliant += 1

    # NPM packages
    total += 1
    if npm_comp["upgradable"] == 0:
        compliant += 1

    # Docker images (just check if we have any old ones)
    total += 1
    old_images = len([i for i in docker_comp["images"] if "week" in i.get("created", "") or "month" in i.get("created", "") or "year" in i.get("created", "")])
    if old_images == 0:
        compliant += 1

    return round((compliant / total) * 100) if total > 0 else 100


def main():
    period = "daily"
    output_format = "json"
    include_fixes = True

    for arg in sys.argv[1:]:
        if arg.startswith("period="):
            period = arg.split("=", 1)[1]
        elif arg.startswith("output="):
            output_format = arg.split("=", 1)[1]
        elif arg.startswith("include_fixes="):
            include_fixes = arg.split("=", 1)[1].lower() == "true"

    patch_status = get_os_patch_status()
    pip_comp = get_pip_compliance()
    npm_comp = get_npm_compliance()
    docker_comp = get_docker_compliance()
    compliance_score = calculate_compliance_score(patch_status, pip_comp, npm_comp, docker_comp)

    report = {
        "report_type": f"Patch Compliance ({period})",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "period": period,
        "hostname": platform.node(),
        "compliance_score": f"{compliance_score}%",
        "summary": {
            "os_pending_patches": patch_status["pending_updates"],
            "os_security_patches": patch_status["security_updates"],
            "pip_upgradable": pip_comp["upgradable"],
            "npm_upgradable": npm_comp["upgradable"],
            "docker_images": docker_comp["total_images"]
        },
        "details": {
            "os": patch_status,
            "pip": pip_comp,
            "npm": npm_comp,
            "docker": docker_comp
        }
    }

    if include_fixes:
        fixes = []
        if patch_status["pending_updates"] > 0:
            fixes.append({
                "component": "os",
                "action": "Run the linux_patch or win_patch script to install pending updates",
                "priority": "high" if patch_status["security_updates"] > 0 else "medium"
            })
        if pip_comp["upgradable"] > 0:
            fixes.append({
                "component": "pip",
                "action": f"Upgrade {pip_comp['upgradable']} package(s): " +
                          ", ".join(p["name"] for p in pip_comp["packages"][:5]),
                "priority": "medium"
            })
        if npm_comp["upgradable"] > 0:
            fixes.append({
                "component": "npm",
                "action": f"Upgrade {npm_comp['upgradable']} package(s): " +
                          ", ".join(p["name"] for p in npm_comp["packages"][:5]),
                "priority": "medium"
            })
        report["recommended_fixes"] = fixes

    if output_format == "json":
        print(json.dumps(report, indent=2))
    elif output_format == "table":
        print(f"{'='*60}")
        print(f"  PATCH COMPLIANCE REPORT — {period.upper()}")
        print(f"  Generated: {report['generated_at']}")
        print(f"  Host: {report['hostname']}")
        print(f"  Score: {report['compliance_score']}")
        print(f"{'='*60}")
        print(f"  OS Patches:    {patch_status['pending_updates']} pending ({patch_status['security_updates']} security)")
        print(f"  Pip Packages:  {pip_comp['upgradable']} upgradable")
        print(f"  NPM Packages:  {npm_comp['upgradable']} upgradable")
        print(f"  Docker Images: {docker_comp['total_images']} total")
        if report.get("recommended_fixes"):
            print(f"\n  RECOMMENDED FIXES:")
            for fix in report["recommended_fixes"]:
                print(f"    [{fix['priority'].upper()}] {fix['component']}: {fix['action']}")
        print(f"{'='*60}")
    elif output_format == "csv":
        print("component,status,detail")
        print(f"os,{'compliant' if patch_status['pending_updates']==0 else 'non-compliant'},{patch_status['pending_updates']} pending")
        print(f"pip,{'compliant' if pip_comp['upgradable']==0 else 'non-compliant'},{pip_comp['upgradable']} upgradable")
        print(f"npm,{'compliant' if npm_comp['upgradable']==0 else 'non-compliant'},{npm_comp['upgradable']} upgradable")
        print(f"docker,ok,{docker_comp['total_images']} images")

    sys.exit(0 if compliance_score == 100 else 1)


if __name__ == "__main__":
    main()
