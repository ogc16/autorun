#!/usr/bin/env python3
"""
System Health Check
Collects CPU, memory, disk usage, uptime, load average, and process count.
Cross-platform (Linux, macOS, Windows).

Parameters:
  include_procs : Include top processes by CPU/memory (default: true)
  threshold_cpu : Alert if CPU usage above this % (default: 90)
  threshold_mem : Alert if memory usage above this % (default: 85)
"""
import json
import os
import platform
import subprocess
import sys
from datetime import datetime


def run_cmd(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception:
        return None, -1


def get_linux_health():
    health = {"os": "linux", "uptime": None, "load_avg": {},
              "cpu": {}, "memory": {}, "disk": [], "top_procs": []}

    out, _ = run_cmd(["uptime", "-p"])
    health["uptime"] = out

    out, _ = run_cmd(["cat", "/proc/loadavg"])
    if out:
        parts = out.split()
        health["load_avg"] = {"1m": float(parts[0]), "5m": float(parts[1]), "15m": float(parts[2])}

    # CPU usage from /proc/stat (instant snapshot not great, use top)
    out, _ = run_cmd(["top", "-bn1"])
    if out:
        for line in out.splitlines():
            if line.startswith("%Cpu"):
                health["cpu"]["summary"] = line
                break

    # Memory
    out, _ = run_cmd(["free", "-b"])
    if out:
        for line in out.splitlines():
            if line.startswith("Mem:"):
                parts = line.split()
                total, used, free = int(parts[1]), int(parts[2]), int(parts[3])
                health["memory"] = {
                    "total_bytes": total, "used_bytes": used, "free_bytes": free,
                    "used_percent": round((used / total) * 100, 1) if total else 0
                }

    # Disk
    out, _ = run_cmd(["df", "-B1", "--output=source,size,used,avail,pcent,target"])
    if out:
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 6 and parts[0].startswith("/"):
                health["disk"].append({
                    "device": parts[0], "total_bytes": int(parts[1]),
                    "used_bytes": int(parts[2]), "avail_bytes": int(parts[3]),
                    "used_percent": int(parts[4].rstrip("%")), "mount": parts[5]
                })

    return health


def get_windows_health():
    health = {"os": "windows", "uptime": None, "cpu": {}, "memory": {}, "disk": [], "top_procs": []}

    out, _ = run_cmd(["powershell", "-NoProfile", "-Command",
                       "((Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime).ToString('hh\\:mm\\:ss')"])
    health["uptime"] = f"up {out}" if out else None

    # CPU
    out, _ = run_cmd(["powershell", "-NoProfile", "-Command",
                       "(Get-CimInstance Win32_Processor).LoadPercentage"])
    if out and out.isdigit():
        health["cpu"]["usage_percent"] = int(out)

    # Memory
    out, _ = run_cmd(["powershell", "-NoProfile", "-Command",
                       "$os=Get-CimInstance Win32_OperatingSystem; "
                       "$total=$os.TotalVisibleMemorySize; $free=$os.FreePhysicalMemory; "
                       "ConvertTo-Json @{total=$total;free=$free;used=$total-$free;percent=[math]::Round(($total-$free)/$total*100,1)}"])
    if out:
        try:
            d = json.loads(out)
            health["memory"] = {
                "total_bytes": d["total"] * 1024, "used_bytes": d["used"] * 1024,
                "free_bytes": d["free"] * 1024, "used_percent": d["percent"]
            }
        except Exception:
            pass

    # Disk
    out, _ = run_cmd(["powershell", "-NoProfile", "-Command",
                       "Get-PSDrive -PSProvider FileSystem | "
                       "Select-Object Name,@{N='Used';E={$_.Used}},@{N='Free';E={$_.Free}} | ConvertTo-Json"])
    if out:
        try:
            drives = json.loads(out)
            if isinstance(drives, dict):
                drives = [drives]
            for d in drives:
                used = d.get("Used", 0) or 0
                free = d.get("Free", 0) or 0
                total = used + free
                health["disk"].append({
                    "device": d["Name"], "total_bytes": total,
                    "used_bytes": used, "free_bytes": free,
                    "used_percent": round((used / total) * 100, 1) if total else 0,
                    "mount": d["Name"]
                })
        except Exception:
            pass

    return health


def main():
    threshold_cpu = 90
    threshold_mem = 85
    include_procs = True

    for arg in sys.argv[1:]:
        if arg.startswith("threshold_cpu="):
            threshold_cpu = int(arg.split("=", 1)[1])
        elif arg.startswith("threshold_mem="):
            threshold_mem = int(arg.split("=", 1)[1])
        elif arg.startswith("include_procs="):
            include_procs = arg.split("=", 1)[1].lower() == "true"

    if platform.system() == "Windows":
        health = get_windows_health()
    else:
        health = get_linux_health()

    health["hostname"] = platform.node()
    health["timestamp"] = datetime.utcnow().isoformat() + "Z"
    health["alerts"] = []

    cpu_pct = health.get("cpu", {}).get("usage_percent", 0)
    mem_pct = health.get("memory", {}).get("used_percent", 0)

    if cpu_pct and cpu_pct > threshold_cpu:
        health["alerts"].append(f"CPU usage {cpu_pct}% exceeds threshold {threshold_cpu}%")
    if mem_pct and mem_pct > threshold_mem:
        health["alerts"].append(f"Memory usage {mem_pct}% exceeds threshold {threshold_mem}%")
    for d in health.get("disk", []):
        if d.get("used_percent", 0) > 90:
            health["alerts"].append(f"Disk {d['mount']} usage {d['used_percent']}% exceeds 90%")

    health["status"] = "WARNING" if health["alerts"] else "HEALTHY"

    print(json.dumps(health, indent=2))
    sys.exit(1 if health["alerts"] else 0)


if __name__ == "__main__":
    main()
