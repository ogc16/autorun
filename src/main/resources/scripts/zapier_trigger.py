#!/usr/bin/env python3
"""
Zapier Integration — Webhook Trigger & Workflow Automation
Triggers Zapier webhooks from AutoRun to connect thousands of apps
and automate client workflows. Supports payload data from script
execution results, alerts, and system events.

Parameters:
  action     : trigger, list_zaps, test_webhook (default: trigger)
  webhook_url : Zapier webhook URL (required — or env: ZAPIER_WEBHOOK_URL)
  zap_name   : Friendly name for the zap/event (default: AutoRun Event)
  event_type : Event type: execution_complete, alert, patch_report,
               health_check, custom (default: custom)
  payload    : JSON string of data to send to Zapier (default: {})
  source     : Source system identifier (default: autorun)
  priority   : Event priority: low, normal, high, critical (default: normal)
  callback_url : URL to receive Zapier response (optional)
  retry_count : Number of retries on failure (default: 3)
  log_dir   : Directory for logs (default: /var/log/autorun-patches)
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime


def trigger_webhook(webhook_url, payload, retries, log_file):
    """Send payload to Zapier webhook with retries."""
    attempts = 0
    last_error = None

    while attempts <= retries:
        attempts += 1
        log(f"  Attempt {attempts}/{retries + 1}", log_file)
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(webhook_url, data=data, headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            })
            resp = urllib.request.urlopen(req, timeout=30)
            status = resp.status
            body = resp.read().decode()
            log(f"  Response: {status} — {body[:200]}", log_file)
            return {"success": True, "status_code": status, "response": body[:500],
                    "attempts": attempts}
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.read().decode()[:300]}"
            log(f"  Error: {last_error}", log_file)
            if e.code >= 500 and attempts <= retries:
                import time
                time.sleep(2 ** attempts)
        except Exception as e:
            last_error = str(e)
            log(f"  Error: {last_error}", log_file)
            if attempts <= retries:
                import time
                time.sleep(2 ** attempts)

    return {"success": False, "error": last_error, "attempts": attempts}


def build_event_payload(event_type, source, priority, zap_name, payload):
    """Build a structured Zapier event payload."""
    return {
        "event": {
            "type": event_type,
            "source": source,
            "priority": priority,
            "name": zap_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "hostname": os.uname().nodename if hasattr(os, "uname") else os.environ.get("COMPUTERNAME", "unknown")
        },
        "data": payload
    }


def test_webhook(webhook_url, log_file):
    """Send a test ping to verify webhook connectivity."""
    log("Testing webhook connectivity", log_file)
    test_payload = {
        "event": {
            "type": "test",
            "source": "autorun",
            "name": "Webhook Test",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        "data": {"message": "AutoRun webhook connectivity test", "ping": True}
    }
    return trigger_webhook(webhook_url, test_payload, 0, log_file)


def trigger_from_execution(webhook_url, execution_data, log_file):
    """Build and send an execution_complete event."""
    event_payload = build_event_payload(
        "execution_complete", "autorun", "normal", "Script Execution Complete",
        {
            "script": execution_data.get("script_name", "unknown"),
            "status": execution_data.get("status", "unknown"),
            "duration_ms": execution_data.get("duration_ms", 0),
            "exit_code": execution_data.get("exit_code", -1),
            "output_summary": execution_data.get("output", "")[:500]
        }
    )
    return trigger_webhook(webhook_url, event_payload, 3, log_file)


def trigger_from_alert(webhook_url, alert_data, log_file):
    """Build and send a system alert event."""
    priority = alert_data.get("severity", "normal")
    event_payload = build_event_payload(
        "alert", "autorun", priority, f"System Alert: {alert_data.get('title', 'Unknown')}",
        {
            "title": alert_data.get("title", "Unknown Alert"),
            "severity": priority,
            "message": alert_data.get("message", ""),
            "host": alert_data.get("host", os.environ.get("COMPUTERNAME", "unknown")),
            "metric": alert_data.get("metric", ""),
            "value": alert_data.get("value", ""),
            "threshold": alert_data.get("threshold", "")
        }
    )
    return trigger_webhook(webhook_url, event_payload, 3, log_file)


def trigger_patch_report(webhook_url, report_data, log_file):
    """Build and send a patch compliance report event."""
    event_payload = build_event_payload(
        "patch_report", "autorun", "normal", "Patch Compliance Report",
        {
            "compliance_status": report_data.get("status", "unknown"),
            "total_packages": report_data.get("total_packages", 0),
            "upgraded": report_data.get("upgraded", 0),
            "failed": report_data.get("failed", 0),
            "reboot_required": report_data.get("reboot_required", False),
            "summary": report_data.get("summary", "")
        }
    )
    return trigger_webhook(webhook_url, event_payload, 3, log_file)


def log(msg, log_file):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if log_file:
        with open(log_file, "a") as f:
            f.write(line + "\n")


def main():
    action = "trigger"
    webhook_url = os.environ.get("ZAPIER_WEBHOOK_URL", "")
    zap_name = "AutoRun Event"
    event_type = "custom"
    payload = "{}"
    source = "autorun"
    priority = "normal"
    callback_url = ""
    retry_count = 3
    log_dir = "/var/log/autorun-patches"

    for arg in sys.argv[1:]:
        if arg.startswith("action="):
            action = arg.split("=", 1)[1]
        elif arg.startswith("webhook_url="):
            webhook_url = arg.split("=", 1)[1]
        elif arg.startswith("zap_name="):
            zap_name = arg.split("=", 1)[1]
        elif arg.startswith("event_type="):
            event_type = arg.split("=", 1)[1]
        elif arg.startswith("payload="):
            payload = arg.split("=", 1)[1]
        elif arg.startswith("source="):
            source = arg.split("=", 1)[1]
        elif arg.startswith("priority="):
            priority = arg.split("=", 1)[1]
        elif arg.startswith("callback_url="):
            callback_url = arg.split("=", 1)[1]
        elif arg.startswith("retry_count="):
            retry_count = int(arg.split("=", 1)[1])
        elif arg.startswith("log_dir="):
            log_dir = arg.split("=", 1)[1]

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"zapier-{datetime.now().strftime('%Y%m%d')}.log")

    if not webhook_url:
        print(json.dumps({"error": "webhook_url is required (set ZAPIER_WEBHOOK_URL env var)"}))
        sys.exit(1)

    output = {"action": action, "timestamp": datetime.utcnow().isoformat() + "Z"}

    try:
        payload_data = json.loads(payload) if isinstance(payload, str) else payload
    except json.JSONDecodeError:
        payload_data = {"raw": payload}

    if action == "trigger":
        log(f"Zapier trigger — event={event_type}, priority={priority}", log_file)
        event_payload = build_event_payload(event_type, source, priority, zap_name, payload_data)
        output["result"] = trigger_webhook(webhook_url, event_payload, retry_count, log_file)
    elif action == "test_webhook":
        log("Zapier webhook test", log_file)
        output["result"] = test_webhook(webhook_url, log_file)
    elif action == "execution_complete":
        log("Zapier execution_complete event", log_file)
        output["result"] = trigger_from_execution(webhook_url, payload_data, log_file)
    elif action == "alert":
        log(f"Zapier alert event — severity={priority}", log_file)
        output["result"] = trigger_from_alert(webhook_url, payload_data, log_file)
    elif action == "patch_report":
        log("Zapier patch_report event", log_file)
        output["result"] = trigger_patch_report(webhook_url, payload_data, log_file)
    else:
        print(json.dumps({"error": f"Unknown action: {action}"}))
        sys.exit(1)

    success = output.get("result", {}).get("success", False)
    print(json.dumps(output, indent=2))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
