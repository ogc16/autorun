#!/usr/bin/env python3
"""
Daily Report Generator
Aggregates system health, patch status, backups, and alerts into
a single daily report file or email. Cross-platform.

Parameters:
  output     : Output format: json, text, html (default: text)
  output_file: File path to write report (default: stdout)
  email_to   : Email address to send report to (default: none)
  sections   : Comma-separated sections (default: all)
              Options: health, patches, backups, security, alerts
"""
import glob
import json
import os
import platform
import subprocess
import sys
from datetime import datetime


def run_cmd(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception:
        return None, -1


def get_health_summary():
    section = {"title": "System Health", "data": {}, "issues": []}

    # CPU
    if platform.system() == "Linux":
        out, _ = run_cmd(["uptime"])
        section["data"]["uptime"] = out

        out, _ = run_cmd(["free", "-h"])
        section["data"]["memory"] = out

        out, _ = run_cmd(["df", "-h", "--output=target,size,used,avail,pcent"])
        section["data"]["disk"] = out

        out, _ = run_cmd(["cat", "/proc/loadavg"])
        section["data"]["load_avg"] = out

    elif platform.system() == "Windows":
        out, _ = run_cmd(["powershell", "-NoProfile", "-Command",
                           "$os=Get-CimInstance Win32_OperatingSystem; "
                           "$cpu=(Get-CimInstance Win32_Processor).LoadPercentage; "
                           "$total=[math]::Round($os.TotalVisibleMemorySize/1MB,1); "
                           "$free=[math]::Round($os.FreePhysicalMemory/1MB,1); "
                           "Write-Host \"CPU: ${cpu}%%\"; "
                           "Write-Host \"Memory: ${free}GB free / ${total}GB total\"; "
                           "Write-Host \"OS: $($os.Caption)\"; "
                           "Write-Host \"Uptime: $((Get-Date) - $os.LastBootUpTime)\""])
        section["data"]["summary"] = out

    return section


def get_patch_summary():
    section = {"title": "Patch Status", "data": {}, "issues": []}

    if platform.system() == "Linux":
        if os.path.exists("/usr/bin/apt"):
            out, rc = run_cmd(["apt", "list", "--upgradable"])
            if rc == 0 and out:
                upgradable = [l for l in out.splitlines() if "upgradable" in l]
                section["data"]["upgradable_count"] = len(upgradable)
                if upgradable:
                    section["data"]["packages"] = upgradable[:20]
                    section["issues"].append(f"{len(upgradable)} APT package(s) upgradable")

        if os.path.exists("/var/run/reboot-required"):
            section["data"]["reboot_required"] = True
            section["issues"].append("System reboot required")

    # pip
    out, rc = run_cmd([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if rc == 0 and out:
        try:
            outdated = json.loads(out)
            section["data"]["pip_upgradable"] = len(outdated)
            if outdated:
                section["data"]["pip_packages"] = [p["name"] for p in outdated[:10]]
                section["issues"].append(f"{len(outdated)} pip package(s) upgradable")
        except json.JSONDecodeError:
            pass

    return section


def get_backup_summary():
    section = {"title": "Backup Status", "data": {}, "issues": []}

    backup_dirs = ["/var/backups", "/backup", os.path.expanduser("~/backups")]
    for d in backup_dirs:
        if os.path.isdir(d):
            files = sorted(glob.glob(os.path.join(d, "*")))
            recent = [f for f in files if os.path.getmtime(f) > datetime.now().timestamp() - 86400]
            section["data"][d] = {"total": len(files), "recent_24h": len(recent)}
            if not recent:
                section["issues"].append(f"No backups in last 24h in {d}")

    if not section["data"]:
        section["data"]["note"] = "No backup directories found"

    return section


def get_security_summary():
    section = {"title": "Security", "data": {}, "issues": []}

    if platform.system() == "Linux":
        # Failed logins
        out, _ = run_cmd(["grep", "-c", "Failed password", "/var/log/auth.log"])
        if out and out.isdigit():
            section["data"]["failed_logins_24h"] = int(out)
            if int(out) > 100:
                section["issues"].append(f"{out} failed login attempts detected")

        # Active users
        out, _ = run_cmd(["who"])
        if out:
            users = [l.split()[0] for l in out.splitlines() if l.strip()]
            section["data"]["active_users"] = list(set(users))

    return section


def get_alerts_log():
    section = {"title": "Recent Alerts", "data": {"alerts": []}, "issues": []}

    log_dirs = ["/var/log/autorun-patches", os.path.join(os.environ.get("TEMP", "."), "autorun-patches")]
    for d in log_dirs:
        if os.path.isdir(d):
            for f in sorted(glob.glob(os.path.join(d, "*.log")), reverse=True)[:3]:
                try:
                    with open(f) as fh:
                        lines = fh.readlines()[-10:]
                        section["data"]["alerts"].append({
                            "file": os.path.basename(f),
                            "last_lines": [l.strip() for l in lines]
                        })
                except Exception:
                    pass

    return section


def format_text(report):
    lines = []
    lines.append("=" * 60)
    lines.append(f"  DAILY REPORT — {report['generated_at']}")
    lines.append(f"  Host: {report['hostname']}")
    lines.append(f"  OS: {report['os']}")
    lines.append("=" * 60)

    for section in report["sections"]:
        lines.append(f"\n  [{section['title'].upper()}]")
        for k, v in section["data"].items():
            if isinstance(v, list):
                lines.append(f"    {k}:")
                for item in v[:10]:
                    if isinstance(item, dict):
                        lines.append(f"      - {json.dumps(item)}")
                    else:
                        lines.append(f"      - {item}")
            else:
                lines.append(f"    {k}: {v}")
        if section["issues"]:
            lines.append(f"    ISSUES:")
            for issue in section["issues"]:
                lines.append(f"      ⚠ {issue}")

    total_issues = sum(len(s["issues"]) for s in report["sections"])
    lines.append(f"\n{'='*60}")
    lines.append(f"  TOTAL ISSUES: {total_issues}")
    lines.append(f"  STATUS: {'ALL CLEAR' if total_issues == 0 else 'ACTION REQUIRED'}")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    output_format = "text"
    output_file = None
    email_to = ""
    sections_raw = "all"

    for arg in sys.argv[1:]:
        if arg.startswith("output="):
            output_format = arg.split("=", 1)[1]
        elif arg.startswith("output_file="):
            output_file = arg.split("=", 1)[1]
        elif arg.startswith("email_to="):
            email_to = arg.split("=", 1)[1]
        elif arg.startswith("sections="):
            sections_raw = arg.split("=", 1)[1]

    ALL_SECTIONS = {
        "health": get_health_summary,
        "patches": get_patch_summary,
        "backups": get_backup_summary,
        "security": get_security_summary,
        "alerts": get_alerts_log,
    }

    if sections_raw == "all":
        section_names = list(ALL_SECTIONS.keys())
    else:
        section_names = [s.strip() for s in sections_raw.split(",")]

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "hostname": platform.node(),
        "os": platform.system(),
        "sections": []
    }

    for name in section_names:
        if name in ALL_SECTIONS:
            report["sections"].append(ALL_SECTIONS[name]())

    total_issues = sum(len(s["issues"]) for s in report["sections"])
    report["summary"] = {
        "total_sections": len(report["sections"]),
        "total_issues": total_issues,
        "status": "ALL CLEAR" if total_issues == 0 else "ACTION REQUIRED"
    }

    if output_format == "json":
        content = json.dumps(report, indent=2)
    else:
        content = format_text(report)

    if output_file:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w") as f:
            f.write(content)
        print(f"Report written to {output_file}")
    else:
        print(content)

    if email_to:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(content)
            msg["Subject"] = f"Daily Report — {platform.node()} — {report['summary']['status']}"
            msg["To"] = email_to
            with smtplib.SMTP("localhost") as s:
                s.send_message(msg)
            print(f"Report emailed to {email_to}")
        except Exception as e:
            print(f"Email failed: {e}")

    sys.exit(1 if total_issues > 0 else 0)


if __name__ == "__main__":
    main()
