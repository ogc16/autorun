#!/usr/bin/env python3
"""
SSL Certificate Checker
Checks SSL certificate expiry for one or more hosts.

Parameters:
  hosts    : Comma-separated list of host:port pairs (required)
  warn_days: Warning threshold in days (default: 30)
"""
import json
import socket
import ssl
import sys
from datetime import datetime, timezone
from typing import List


def parse_hosts(raw: str) -> List[str]:
    hosts = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            entry = entry + ":443"
        hosts.append(entry)
    return hosts


def check_cert(host: str, port: int, warn_days: int) -> dict:
    result = {"host": host, "port": port, "ok": False, "error": None,
              "issuer": None, "subject": None, "not_after": None, "days_left": None, "warning": False}
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                not_after_str = cert.get("notAfter", "")
                not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                days_left = (not_after - datetime.now(timezone.utc)).days
                issuer_parts = [v for (k, v) in cert.get("issuer", [("", "")]) if k == "organizationName"]
                subject_parts = [v for (k, v) in cert.get("subject", [("", "")]) if k == "commonName"]
                result.update({
                    "ok": True,
                    "issuer": issuer_parts[0] if issuer_parts else "Unknown",
                    "subject": subject_parts[0] if subject_parts else host,
                    "not_after": not_after.isoformat(),
                    "days_left": days_left,
                    "warning": days_left <= warn_days
                })
    except Exception as e:
        result["error"] = str(e)
    return result


def main():
    hosts_raw = ""
    warn_days = 30
    for arg in sys.argv[1:]:
        if arg.startswith("hosts="):
            hosts_raw = arg.split("=", 1)[1]
        elif arg.startswith("warn_days="):
            try:
                warn_days = int(arg.split("=", 1)[1])
            except ValueError:
                pass

    if not hosts_raw:
        print("ERROR: hosts parameter is required (comma-separated host:port pairs)")
        sys.exit(1)

    hosts = parse_hosts(hosts_raw)
    results = []
    all_ok = True
    for entry in hosts:
        parts = entry.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 443
        r = check_cert(host, port, warn_days)
        results.append(r)
        if not r["ok"] or r["warning"]:
            all_ok = False

    summary = {
        "checked": len(results),
        "all_ok": all_ok,
        "warn_days": warn_days,
        "results": results
    }
    print(json.dumps(summary, indent=2))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
