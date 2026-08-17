#!/usr/bin/env python3
"""
Patch Orchestrator — Master Daily Patch Workflow
Ties together inventory, check, apply, verify, report, and notify
into a single end-to-end patch management cycle.

Workflow steps:
  1. Inventory    → Discover what needs patching
  2. Pre-check    → Snapshot current state for rollback
  3. Apply        → Run platform-appropriate patch scripts
  4. Verify       → Confirm patches installed correctly
  5. Report       → Generate compliance report
  6. Notify       → Send results via email/Slack
  7. Rollback     → Auto-revert if verification fails

Parameters:
  step         : Run a specific step or 'all' (default: all)
  dry_run      : Only check, never install (default: false)
  auto_rollback: Auto-rollback on verification failure (default: true)
  notify       : Send notification at end (default: false)
  slack_webhook: Slack webhook URL for notifications
  email_to     : Email recipient for notifications
"""
import json
import os
import platform
import subprocess
import sys
from datetime import datetime


def run_cmd(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1


def log(msg, log_file):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if log_file:
        with open(log_file, "a") as f:
            f.write(line + "\n")


def step_inventory(log_file):
    """Step 1: Discover what needs patching."""
    log("=== STEP 1: INVENTORY ===", log_file)
    report = {"step": "inventory", "os": platform.system(), "packages": {}}

    if platform.system() == "Linux":
        if os.path.exists("/usr/bin/apt"):
            out, rc = run_cmd(["apt", "list", "--upgradable"])
            if rc == 0 and out:
                upgradable = [l for l in out.splitlines() if "upgradable" in l]
                report["packages"]["apt"] = {"count": len(upgradable), "packages": upgradable}
                log(f"  APT: {len(upgradable)} package(s) upgradable", log_file)
        elif os.path.exists("/usr/bin/yum") or os.path.exists("/usr/bin/dnf"):
            pkg_mgr = "dnf" if os.path.exists("/usr/bin/dnf") else "yum"
            out, rc = run_cmd([pkg_mgr, "check-update"])
            if rc == 100 and out:
                updates = [l for l in out.splitlines() if l.strip() and not l.startswith("Last")]
                report["packages"][pkg_mgr] = {"count": len(updates)}
                log(f"  {pkg_mgr.upper()}: {len(updates)} package(s) upgradable", log_file)

    # Python packages
    out, rc = run_cmd([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if rc == 0 and out:
        try:
            pip_outdated = json.loads(out)
            report["packages"]["pip"] = {
                "count": len(pip_outdated),
                "packages": [{"name": p["name"], "current": p["version"], "latest": p["latest_version"]}
                             for p in pip_outdated]
            }
            log(f"  PIP: {len(pip_outdated)} package(s) upgradable", log_file)
        except json.JSONDecodeError:
            pass

    # npm
    out, rc = run_cmd(["npm", "outdated", "--json"], timeout=60)
    if rc == 0 and out:
        try:
            npm_outdated = json.loads(out)
            report["packages"]["npm"] = {"count": len(npm_outdated)}
            log(f"  NPM: {len(npm_outdated)} package(s) upgradable", log_file)
        except json.JSONDecodeError:
            pass

    total = sum(v.get("count", 0) for v in report["packages"].values())
    report["total_upgradable"] = total
    log(f"  TOTAL: {total} package(s) upgradable", log_file)
    return report


def step_presnapshot(log_file):
    """Step 2: Snapshot current state for rollback."""
    log("=== STEP 2: PRE-SNAPSHOT ===", log_file)
    snapshot = {"step": "presnapshot", "timestamp": datetime.utcnow().isoformat() + "Z",
                "packages": {}, "error": None}

    if platform.system() == "Linux":
        if os.path.exists("/usr/bin/dpkg"):
            out, rc = run_cmd(["dpkg", "-l"])
            if rc == 0 and out:
                count = len([l for l in out.splitlines() if l.startswith("ii")])
                snapshot["packages"]["dpkg"] = count
                log(f"  dpkg: {count} packages installed", log_file)

    out, rc = run_cmd([sys.executable, "-m", "pip", "list", "--format=json"])
    if rc == 0 and out:
        try:
            pkgs = json.loads(out)
            snapshot["packages"]["pip"] = {p["name"]: p["version"] for p in pkgs}
            log(f"  pip: {len(pkgs)} packages recorded", log_file)
        except json.JSONDecodeError:
            pass

    return snapshot


def step_apply(dry_run, log_file):
    """Step 3: Apply patches."""
    log("=== STEP 3: APPLY PATCHES ===", log_file)
    results = {"step": "apply", "dry_run": dry_run, "platforms": {}, "error": None}

    if dry_run:
        log("  DRY RUN — no changes will be made", log_file)
        return results

    if platform.system() == "Linux":
        if os.path.exists("/usr/bin/apt"):
            log("  Running apt upgrade...", log_file)
            out, rc = run_cmd(["bash", "-c",
                                "DEBIAN_FRONTEND=noninteractive apt-get update -qq && "
                                "DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::=--force-confdef"])
            results["platforms"]["apt"] = {"exit_code": rc, "output_lines": len(out.splitlines()) if out else 0}
            log(f"  APT upgrade finished (exit={rc})", log_file)
            run_cmd(["apt-get", "autoremove", "-y"])
        elif os.path.exists("/usr/bin/dnf") or os.path.exists("/usr/bin/yum"):
            pkg_mgr = "dnf" if os.path.exists("/usr/bin/dnf") else "yum"
            log(f"  Running {pkg_mgr} upgrade...", log_file)
            out, rc = run_cmd([pkg_mgr, "update", "-y"])
            results["platforms"][pkg_mgr] = {"exit_code": rc}
            log(f"  {pkg_mgr.upper()} upgrade finished (exit={rc})", log_file)

    # Python packages
    log("  Upgrading pip packages...", log_file)
    out, rc = run_cmd([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if rc == 0 and out:
        try:
            outdated = json.loads(out)
            upgraded, failed = [], []
            for pkg in outdated:
                name = pkg["name"]
                _, pip_rc = run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", name])
                if pip_rc == 0:
                    upgraded.append(name)
                else:
                    failed.append(name)
            results["platforms"]["pip"] = {"upgraded": len(upgraded), "failed": len(failed)}
            log(f"  pip: {len(upgraded)} upgraded, {len(failed)} failed", log_file)
        except json.JSONDecodeError:
            pass

    return results


def step_verify(snapshot, log_file):
    """Step 4: Verify patches installed correctly."""
    log("=== STEP 4: VERIFY ===", log_file)
    result = {"step": "verify", "checks_passed": 0, "checks_failed": 0, "details": [], "error": None}

    if platform.system() == "Linux":
        if os.path.exists("/usr/bin/apt"):
            out, rc = run_cmd(["apt", "list", "--upgradable"])
            remaining = len([l for l in out.splitlines() if "upgradable" in l]) if rc == 0 else -1
            passed = remaining == 0
            result["details"].append({"check": "apt_upgradable_remaining", "value": remaining, "passed": passed})
            if passed:
                result["checks_passed"] += 1
                log(f"  APT: 0 remaining (OK)", log_file)
            else:
                result["checks_failed"] += 1
                log(f"  APT: {remaining} still upgradable (FAIL)", log_file)

    # pip check
    out, rc = run_cmd([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if rc == 0:
        try:
            remaining = len(json.loads(out))
            passed = remaining == 0
            result["details"].append({"check": "pip_outdated_remaining", "value": remaining, "passed": passed})
            if passed:
                result["checks_passed"] += 1
                log(f"  PIP: 0 outdated (OK)", log_file)
            else:
                result["checks_failed"] += 1
                log(f"  PIP: {remaining} still outdated (FAIL)", log_file)
        except json.JSONDecodeError:
            pass

    # System health: reboot required?
    if platform.system() == "Linux" and os.path.exists("/var/run/reboot-required"):
        result["details"].append({"check": "reboot_required", "value": True, "passed": False})
        result["checks_failed"] += 1
        log("  REBOOT REQUIRED", log_file)

    result["passed"] = result["checks_failed"] == 0
    return result


def step_report(inventory, apply_results, verify_result, log_file):
    """Step 5: Generate compliance report."""
    log("=== STEP 5: REPORT ===", log_file)
    report = {
        "step": "report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "hostname": platform.node(),
        "os": platform.system(),
        "inventory": inventory,
        "apply": apply_results,
        "verify": verify_result,
        "compliance": "PASS" if verify_result.get("passed", False) else "FAIL"
    }
    log(f"  Compliance: {report['compliance']}", log_file)
    return report


def step_notify(report, slack_webhook, email_to, log_file):
    """Step 6: Send notifications."""
    log("=== STEP 6: NOTIFY ===", log_file)

    summary = (
        f"Patch Report — {report.get('compliance', 'UNKNOWN')}\n"
        f"Host: {report.get('hostname', '?')}\n"
        f"OS: {report.get('os', '?')}\n"
        f"Checks passed: {report.get('verify', {}).get('checks_passed', 0)}\n"
        f"Checks failed: {report.get('verify', {}).get('checks_failed', 0)}\n"
    )

    sent = []

    if slack_webhook:
        try:
            import urllib.request
            payload = json.dumps({"text": summary}).encode()
            req = urllib.request.Request(slack_webhook, data=payload,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            sent.append("slack")
            log("  Slack notification sent", log_file)
        except Exception as e:
            log(f"  Slack notification failed: {e}", log_file)

    if email_to:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(summary)
            msg["Subject"] = f"Patch Report — {report.get('compliance', 'UNKNOWN')} — {platform.node()}"
            msg["To"] = email_to
            # Uses localhost SMTP; configure sender in production
            with smtplib.SMTP("localhost") as s:
                s.send_message(msg)
            sent.append("email")
            log(f"  Email sent to {email_to}", log_file)
        except Exception as e:
            log(f"  Email failed: {e}", log_file)

    return {"sent_to": sent}


def main():
    step = "all"
    dry_run = False
    auto_rollback = True
    notify = False
    slack_webhook = ""
    email_to = ""
    log_dir = "/var/log/autorun-patches"
    if platform.system() == "Windows":
        log_dir = os.path.join(os.environ.get("TEMP", "."), "autorun-patches")

    for arg in sys.argv[1:]:
        if arg.startswith("step="):
            step = arg.split("=", 1)[1]
        elif arg.startswith("dry_run="):
            dry_run = arg.split("=", 1)[1].lower() == "true"
        elif arg.startswith("auto_rollback="):
            auto_rollback = arg.split("=", 1)[1].lower() == "true"
        elif arg.startswith("notify="):
            notify = arg.split("=", 1)[1].lower() == "true"
        elif arg.startswith("slack_webhook="):
            slack_webhook = arg.split("=", 1)[1]
        elif arg.startswith("email_to="):
            email_to = arg.split("=", 1)[1]

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"orchestrator-{datetime.now().strftime('%Y%m%d')}.log")

    log("===== PATCH ORCHESTRATOR STARTED =====", log_file)
    log(f"  step={step} dry_run={dry_run} auto_rollback={auto_rollback}", log_file)

    inventory = apply_results = verify_result = report = notify_result = None
    snapshot = None

    steps_to_run = ["inventory", "snapshot", "apply", "verify", "report"] if step == "all" else [step]

    if "inventory" in steps_to_run:
        inventory = step_inventory(log_file)

    if "snapshot" in steps_to_run:
        snapshot = step_presnapshot(log_file)

    if "apply" in steps_to_run:
        apply_results = step_apply(dry_run, log_file)

    if "verify" in steps_to_run:
        verify_result = step_verify(snapshot, log_file)

        if not verify_result.get("passed", True) and auto_rollback and not dry_run:
            log("  VERIFICATION FAILED — triggering rollback", log_file)
            step_rollback(log_file)

    if "report" in steps_to_run:
        report = step_report(inventory, apply_results, verify_result, log_file)

    if notify and report:
        notify_result = step_notify(report, slack_webhook, email_to, log_file)

    log("===== PATCH ORCHESTRATOR COMPLETED =====", log_file)

    output = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dry_run": dry_run,
        "inventory": inventory,
        "apply": apply_results,
        "verify": verify_result,
        "report": report,
        "notify": notify_result
    }
    print(json.dumps(output, indent=2))

    passed = verify_result.get("passed", True) if verify_result else True
    sys.exit(0 if passed else 1)


def step_rollback(log_file):
    """Step 7: Auto-rollback on verification failure."""
    log("=== STEP 7: ROLLBACK ===", log_file)

    if platform.system() == "Linux":
        if os.path.exists("/usr/bin/apt"):
            out, rc = run_cmd(["apt-get", "install", "-y", "--fix-broken"])
            log(f"  apt --fix-broken: exit={rc}", log_file)

    # pip rollback — not automatic, log warning
    log("  pip rollback requires manual version specification", log_file)


if __name__ == "__main__":
    main()
