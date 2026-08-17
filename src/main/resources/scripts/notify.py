#!/usr/bin/env python3
"""
Notify Script
Sends alerts via email or Slack when failures occur.
Cross-platform. Can be called standalone or chained from other scripts.

Parameters:
  channel   : Notification channel: slack, email, both (default: both)
  title     : Alert title (required)
  body      : Alert body text (required)
  severity  : Severity level: info, warning, critical (default: warning)
  slack_webhook : Slack webhook URL (or env: SLACK_WEBHOOK_URL)
  email_to  : Recipient email address (or env: ALERT_EMAIL_TO)
  email_from: Sender email (default: autorun@localhost)
  smtp_host : SMTP server (default: localhost)
  smtp_port : SMTP port (default: 25)
"""
import json
import os
import platform
import smtplib
import sys
import urllib.request
from datetime import datetime


def send_slack(webhook_url, title, body, severity):
    emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(severity, "📢")

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {title}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity.upper()}"},
                    {"type": "mrkdwn", "text": f"*Host:*\n{platform.node()}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"}
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Details:*\n{body}"}
            }
        ]
    }

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(webhook_url, data=data,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        return {"channel": "slack", "success": True, "status_code": resp.status}
    except Exception as e:
        return {"channel": "slack", "success": False, "error": str(e)}


def send_email(smtp_host, smtp_port, email_from, email_to, title, body, severity):
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = email_from
        msg["To"] = email_to
        msg["Subject"] = f"[{severity.upper()}] {title} — {platform.node()}"

        html_body = f"""
        <html>
        <body>
        <h2>{title}</h2>
        <table border="0" cellpadding="5">
        <tr><td><b>Severity:</b></td><td>{severity.upper()}</td></tr>
        <tr><td><b>Host:</b></td><td>{platform.node()}</td></tr>
        <tr><td><b>Time:</b></td><td>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
        <tr><td><b>OS:</b></td><td>{platform.system()}</td></tr>
        </table>
        <h3>Details</h3>
        <pre>{body}</pre>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))
        msg.attach(MIMEText(f"{title}\n\n{body}", "plain"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
            s.send_message(msg)

        return {"channel": "email", "success": True, "to": email_to}
    except Exception as e:
        return {"channel": "email", "success": False, "error": str(e)}


def main():
    channel = "both"
    title = ""
    body = ""
    severity = "warning"
    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    email_to = os.environ.get("ALERT_EMAIL_TO", "")
    email_from = "autorun@localhost"
    smtp_host = "localhost"
    smtp_port = 25

    for arg in sys.argv[1:]:
        if arg.startswith("channel="):
            channel = arg.split("=", 1)[1]
        elif arg.startswith("title="):
            title = arg.split("=", 1)[1]
        elif arg.startswith("body="):
            body = arg.split("=", 1)[1]
        elif arg.startswith("severity="):
            severity = arg.split("=", 1)[1]
        elif arg.startswith("slack_webhook="):
            slack_webhook = arg.split("=", 1)[1]
        elif arg.startswith("email_to="):
            email_to = arg.split("=", 1)[1]
        elif arg.startswith("email_from="):
            email_from = arg.split("=", 1)[1]
        elif arg.startswith("smtp_host="):
            smtp_host = arg.split("=", 1)[1]
        elif arg.startswith("smtp_port="):
            smtp_port = int(arg.split("=", 1)[1])

    if not title or not body:
        print(json.dumps({"error": "title and body parameters are required"}))
        sys.exit(1)

    results = {"timestamp": datetime.utcnow().isoformat() + "Z", "title": title,
               "severity": severity, "notifications": []}

    if channel in ("slack", "both"):
        if slack_webhook:
            results["notifications"].append(send_slack(slack_webhook, title, body, severity))
        else:
            results["notifications"].append({"channel": "slack", "success": False,
                                              "error": "No webhook URL configured"})

    if channel in ("email", "both"):
        if email_to:
            results["notifications"].append(send_email(smtp_host, smtp_port, email_from,
                                                        email_to, title, body, severity))
        else:
            results["notifications"].append({"channel": "email", "success": False,
                                              "error": "No recipient configured"})

    all_ok = all(n.get("success", False) for n in results["notifications"])
    results["all_sent"] = all_ok

    print(json.dumps(results, indent=2))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
