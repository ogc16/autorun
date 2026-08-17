#!/usr/bin/env python3
"""
Network Diagnostics Script
Automates ping, traceroute, nslookup, and port checks.
Cross-platform.

Parameters:
  targets   : Comma-separated hosts/IPs to test (required)
  ports     : Comma-separated ports to check (default: 80,443,22)
  timeout   : Timeout per check in seconds (default: 5)
  runs      : Number of ping attempts (default: 4)
"""
import json
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


def ping(host, count=4, timeout=5):
    result = {"host": host, "type": "ping", "reachable": False, "avg_ms": None, "loss_pct": None, "error": None}
    if platform.system() == "Windows":
        cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(timeout), host]
    out, rc = run_cmd(cmd, timeout=timeout * count + 10)
    result["reachable"] = rc == 0
    if out:
        for line in out.splitlines():
            if "avg" in line or "Average" in line:
                try:
                    if platform.system() == "Windows":
                        result["avg_ms"] = float(line.split("=")[-1].strip().split()[0])
                    else:
                        parts = line.split("=")[1].strip().split("/")
                        result["avg_ms"] = float(parts[1])
                except Exception:
                    pass
            if "loss" in line.lower() or "Lost" in line:
                try:
                    result["loss_pct"] = float(line.split("%")[0].split()[-1])
                except Exception:
                    pass
    return result


def traceroute(host, max_hops=15, timeout=5):
    result = {"host": host, "type": "traceroute", "hops": [], "error": None}
    if platform.system() == "Windows":
        cmd = ["tracert", "-d", "-h", str(max_hops), host]
    else:
        cmd = ["traceroute", "-m", str(max_hops), "-w", str(timeout), host]
    out, rc = run_cmd(cmd, timeout=max_hops * timeout + 30)
    if out:
        for line in out.splitlines()[1:]:
            result["hops"].append(line.strip())
    else:
        result["error"] = "traceroute failed or not available"
    return result


def nslookup(host):
    result = {"host": host, "type": "nslookup", "ips": [], "error": None}
    out, rc = run_cmd(["nslookup", host], timeout=10)
    if out:
        parsing = False
        for line in out.splitlines():
            if "Address:" in line and "Server:" not in line:
                ip = line.split("Address:")[-1].strip()
                if ip and ip != result["host"]:
                    result["ips"].append(ip)
    return result


def check_port(host, port, timeout=3):
    import socket
    result = {"host": host, "port": port, "type": "port_check", "open": False, "error": None}
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            result["open"] = True
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        result["error"] = str(e)
    return result


def main():
    targets_raw = ""
    ports_raw = "80,443,22"
    timeout = 5
    count = 4

    for arg in sys.argv[1:]:
        if arg.startswith("targets="):
            targets_raw = arg.split("=", 1)[1]
        elif arg.startswith("ports="):
            ports_raw = arg.split("=", 1)[1]
        elif arg.startswith("timeout="):
            timeout = int(arg.split("=", 1)[1])
        elif arg.startswith("runs="):
            count = int(arg.split("=", 1)[1])

    if not targets_raw:
        print(json.dumps({"error": "targets parameter is required"}))
        sys.exit(1)

    targets = [t.strip() for t in targets_raw.split(",") if t.strip()]
    ports = [int(p.strip()) for p in ports_raw.split(",") if p.strip()]

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "targets": targets,
        "results": []
    }

    for host in targets:
        host_results = {
            "host": host,
            "ping": ping(host, count, timeout),
            "nslookup": nslookup(host),
            "ports": [check_port(host, p, timeout) for p in ports]
        }

        open_ports = [p for p in host_results["ports"] if p["open"]]
        host_results["summary"] = {
            "reachable": host_results["ping"]["reachable"],
            "open_ports": len(open_ports),
            "total_ports_checked": len(ports),
            "dns_resolves": len(host_results["nslookup"]["ips"]) > 0
        }

        report["results"].append(host_results)

    report["summary"] = {
        "total_targets": len(targets),
        "reachable": sum(1 for r in report["results"] if r["summary"]["reachable"]),
        "unreachable": sum(1 for r in report["results"] if not r["summary"]["reachable"])
    }

    print(json.dumps(report, indent=2))
    sys.exit(0 if report["summary"]["unreachable"] == 0 else 1)


if __name__ == "__main__":
    main()
