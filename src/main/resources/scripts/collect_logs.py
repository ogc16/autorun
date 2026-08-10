#!/usr/bin/env python3
"""AutoRun sample: collect & summarize log files. Cross-platform (Windows/Linux)."""
import os
import platform
import sys
import time
from pathlib import Path

days = int(sys.argv[1]) if len(sys.argv) > 1 else 7

print(f"[collect_logs] OS={platform.system()} days_back={days}", flush=True)

candidates = []
if platform.system() == "Windows":
    for base in (Path(os.environ.get("TEMP", ".")), Path("C:/Windows/Temp")):
        if base.exists():
            candidates.extend(base.glob("*.log"))
else:
    for base in (Path("/var/log"), Path("/tmp")):
        if base.exists():
            candidates.extend(base.glob("*.log"))

cutoff = time.time() - days * 86400
found, total = 0, 0

for f in sorted(set(candidates)):
    try:
        if f.stat().st_mtime >= cutoff:
            size = f.stat().st_size
            print(f"[collect_logs]   {f}  ({size} bytes)", flush=True)
            found += 1
            total += size
    except OSError:
        continue

print(f"[collect_logs] Found {found} log file(s), total {total} bytes.", flush=True)
if found == 0:
    print("[collect_logs] Nothing to collect.", flush=True)
    sys.exit(0)

print("[collect_logs] Done.", flush=True)
sys.exit(0)
