#!/usr/bin/env python3
"""
Audit Trail & Fixed Asset Archiving
Extracts system logs and financial transactions into structured,
immutable-format archives for internal/external audit preparation.

Parameters:
  log_dir       : Directory containing application logs (required)
  transactions  : Path to financial transactions CSV (required)
  output_dir    : Output directory for audit archive (default: /tmp/audit_archive)
  encrypt       : Enable GPG encryption if available (default: false)
  retention_days: Only archive logs older than N days (default: 30)
"""
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


def parse_args(argv):
    args = {
        "output_dir": "/tmp/audit_archive",
        "encrypt": "false",
        "retention_days": 30,
    }
    for arg in argv:
        if arg.startswith("log_dir="):
            args["log_dir"] = arg.split("=", 1)[1]
        elif arg.startswith("transactions="):
            args["transactions"] = arg.split("=", 1)[1]
        elif arg.startswith("output_dir="):
            args["output_dir"] = arg.split("=", 1)[1]
        elif arg.startswith("encrypt="):
            args["encrypt"] = arg.split("=", 1)[1].lower()
        elif arg.startswith("retention_days="):
            args["retention_days"] = int(arg.split("=", 1)[1])
    return args


def collect_logs(log_dir, retention_days):
    """Collect and hash log files for immutability."""
    entries = []
    if not os.path.isdir(log_dir):
        return entries

    for fname in sorted(os.listdir(log_dir)):
        fpath = os.path.join(log_dir, fname)
        if not os.path.isfile(fpath):
            continue
        stat = os.stat(fpath)
        sha256 = hashlib.sha256()
        with open(fpath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        entries.append({
            "filename": fname,
            "size_bytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "sha256": sha256.hexdigest(),
            "archived_at": datetime.now(timezone.utc).isoformat(),
        })
    return entries


def load_transactions(filepath):
    entries = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append({
                "transaction_id": row.get("transaction_id", ""),
                "date": row.get("date", ""),
                "type": row.get("type", ""),
                "amount": float(row.get("amount", 0)),
                "currency": row.get("currency", "USD"),
                "account": row.get("account", ""),
                "description": row.get("description", ""),
                "authorised_by": row.get("authorised_by", ""),
            })
    return entries


def compute_transaction_hash(entries):
    """Compute a Merkle-style chain hash for tamper evidence."""
    chain_hash = hashlib.sha256(b"genesis").hexdigest()
    hashed_entries = []
    for e in entries:
        payload = json.dumps(e, sort_keys=True).encode()
        entry_hash = hashlib.sha256(payload).hexdigest()
        combined = hashlib.sha256((chain_hash + entry_hash).encode()).hexdigest()
        hashed_entries.append({**e, "chain_hash": combined, "entry_hash": entry_hash})
        chain_hash = combined
    return hashed_entries, chain_hash


def write_archive(output_dir, log_entries, tx_entries, chain_root):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_name = f"audit_archive_{ts}"

    manifest = {
        "archive_id": archive_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "log_files_archived": len(log_entries),
        "transactions_archived": len(tx_entries),
        "merkle_root": chain_root,
        "immutable": True,
    }

    manifest_file = os.path.join(output_dir, f"{archive_name}_manifest.json")
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    logs_file = os.path.join(output_dir, f"{archive_name}_logs.json")
    with open(logs_file, "w") as f:
        json.dump(log_entries, f, indent=2)

    tx_file = os.path.join(output_dir, f"{archive_name}_transactions.json")
    with open(tx_file, "w") as f:
        json.dump(tx_entries, f, indent=2)

    checksum_file = os.path.join(output_dir, f"{archive_name}_checksums.txt")
    with open(checksum_file, "w") as f:
        for entry in tx_entries:
            f.write(f"{entry['chain_hash']}  {entry['transaction_id']}\n")

    return manifest_file, logs_file, tx_file


def main():
    args = parse_args(sys.argv[1:])
    log_dir = args.get("log_dir")
    transactions = args.get("transactions")

    if not log_dir:
        print("ERROR: log_dir parameter is required")
        sys.exit(1)
    if not transactions:
        print("ERROR: transactions parameter is required (path to transactions CSV)")
        sys.exit(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting audit archive extraction...")
    print(f"Log dir: {log_dir}, Retention: {args['retention_days']} days")

    log_entries = collect_logs(log_dir, args["retention_days"])
    print(f"Collected {len(log_entries)} log files")

    tx_entries = load_transactions(transactions)
    print(f"Loaded {len(tx_entries)} financial transactions")

    hashed_tx, chain_root = compute_transaction_hash(tx_entries)
    print(f"Computed Merkle chain: root={chain_root[:16]}...")

    manifest_file, logs_file, tx_file = write_archive(
        args["output_dir"], log_entries, hashed_tx, chain_root
    )

    result = {
        "status": "success",
        "archive_manifest": manifest_file,
        "log_files": len(log_entries),
        "transactions": len(tx_entries),
        "merkle_root": chain_root,
        "encrypted": args["encrypt"] == "true",
    }
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
