#!/usr/bin/env python3
"""Cross-platform disk usage report with threshold alerts."""

import shutil
import sys
import json

THRESHOLD = int(sys.argv[1]) if len(sys.argv) > 1 else 80

results = []
alerts = []

for path in ["/", "/tmp", "C:\\", "D:\\"]:
    try:
        usage = shutil.disk_usage(path)
        pct = round(usage.used / usage.total * 100, 1)
        free_gb = round(usage.free / (1024**3), 2)
        total_gb = round(usage.total / (1024**3), 2)
        entry = {"path": path, "used_pct": pct, "free_gb": free_gb, "total_gb": total_gb}
        results.append(entry)
        if pct >= THRESHOLD:
            alerts.append(entry)
    except (OSError, FileNotFoundError):
        pass

if not results:
    print("No accessible drives found.")
    sys.exit(1)

print("=" * 60)
print("DISK USAGE REPORT")
print("=" * 60)
for r in results:
    flag = " !!! ALERT" if r["used_pct"] >= THRESHOLD else ""
    print(f"  {r['path']:6s}  {r['used_pct']:5.1f}% used  |  {r['free_gb']:.1f} GB free / {r['total_gb']:.1f} GB total{flag}")

if alerts:
    print(f"\nWARNING: {len(alerts)} volume(s) above {THRESHOLD}% threshold!")
    sys.exit(2)
else:
    print(f"\nAll volumes OK (threshold: {THRESHOLD}%).")
    sys.exit(0)
