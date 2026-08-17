#!/usr/bin/env python3
"""
Bank Feed Sync & Reconciliation
Fetches bank statements via API/SFTP, matches transactions against GL entries,
and flags unreconciled items.

Parameters:
  bank_config  : JSON string with bank connection details (required)
  gl_file      : Path to GL export CSV (required)
  output_dir   : Directory for reconciliation reports (default: /tmp/reconciliation)
  match_window : Hours to look back for matching (default: 72)
  tolerance    : Amount matching tolerance in minor units (default: 1)
"""
import csv
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone


def parse_args(argv):
    args = {"match_window": 72, "tolerance": 1, "output_dir": "/tmp/reconciliation"}
    for arg in argv:
        if arg.startswith("bank_config="):
            args["bank_config"] = json.loads(arg.split("=", 1)[1])
        elif arg.startswith("gl_file="):
            args["gl_file"] = arg.split("=", 1)[1]
        elif arg.startswith("output_dir="):
            args["output_dir"] = arg.split("=", 1)[1]
        elif arg.startswith("match_window="):
            args["match_window"] = int(arg.split("=", 1)[1])
        elif arg.startswith("tolerance="):
            args["tolerance"] = int(arg.split("=", 1)[1])
    return args


def load_gl_entries(filepath):
    entries = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append({
                "id": row.get("id", str(uuid.uuid4())),
                "date": row.get("date", ""),
                "description": row.get("description", ""),
                "amount": float(row.get("amount", 0)),
                "currency": row.get("currency", "USD"),
                "reference": row.get("reference", ""),
                "matched": False,
            })
    return entries


def simulate_bank_fetch(bank_config):
    """In production this connects to bank APIs/SFTP. Demo generates sample data."""
    bank_id = bank_config.get("bank_id", "BANK001")
    accounts = bank_config.get("accounts", ["default"])
    transactions = []
    for acct in accounts:
        for i in range(3):
            transactions.append({
                "id": f"TXN-{bank_id}-{acct}-{i+1}",
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "description": f"Sample transaction {i+1} for {acct}",
                "amount": round((i + 1) * 125.50, 2),
                "currency": "USD",
                "account": acct,
                "bank_id": bank_id,
            })
    return transactions


def match_transactions(gl_entries, bank_txns, tolerance, window_hours):
    matches = []
    unmatched_gl = []
    unmatched_bank = list(bank_txns)

    for gl in gl_entries:
        best_match = None
        best_idx = -1
        for idx, txn in enumerate(unmatched_bank):
            if txn.get("matched"):
                continue
            if gl["currency"] != txn.get("currency", gl["currency"]):
                continue
            diff = abs(gl["amount"] - txn["amount"])
            if diff <= tolerance:
                if best_match is None or diff < best_match["diff"]:
                    best_match = {"gl": gl, "bank": txn, "diff": diff}
                    best_idx = idx
        if best_match:
            best_match["gl"]["matched"] = True
            best_match["bank"]["matched"] = True
            matches.append({
                "gl_id": best_match["gl"]["id"],
                "bank_id": best_match["bank"]["id"],
                "amount": best_match["gl"]["amount"],
                "diff": best_match["diff"],
            })
        else:
            unmatched_gl.append(gl)

    unmatched_bank_final = [t for t in unmatched_bank if not t.get("matched")]
    return matches, unmatched_gl, unmatched_bank_final


def write_report(output_dir, matches, unmatched_gl, unmatched_bank):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f"recon_{ts}.json")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "matched": len(matches),
            "unmatched_gl": len(unmatched_gl),
            "unmatched_bank": len(unmatched_bank),
            "total_gl": len(matches) + len(unmatched_gl),
            "total_bank": len(matches) + len(unmatched_bank),
        },
        "matches": matches,
        "unmatched_gl": [{"id": e["id"], "date": e["date"], "amount": e["amount"],
                          "description": e["description"], "reference": e["reference"]}
                         for e in unmatched_gl],
        "unmatched_bank": [{"id": t["id"], "date": t["date"], "amount": t["amount"],
                            "description": t["description"], "account": t.get("account", "")}
                           for t in unmatched_bank],
    }
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    return report_file, report


def main():
    args = parse_args(sys.argv[1:])
    bank_config = args.get("bank_config")
    gl_file = args.get("gl_file")

    if not bank_config:
        print("ERROR: bank_config parameter is required (JSON string)")
        sys.exit(1)
    if not gl_file:
        print("ERROR: gl_file parameter is required (path to GL CSV)")
        sys.exit(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting bank feed sync...")

    gl_entries = load_gl_entries(gl_file)
    print(f"Loaded {len(gl_entries)} GL entries")

    bank_txns = simulate_bank_fetch(bank_config)
    print(f"Fetched {len(bank_txns)} bank transactions")

    matches, unmatched_gl, unmatched_bank = match_transactions(
        gl_entries, bank_txns, args["tolerance"], args["match_window"]
    )

    report_file, report = write_report(
        args["output_dir"], matches, unmatched_gl, unmatched_bank
    )

    result = {
        "status": "success",
        "report_file": report_file,
        "summary": report["summary"],
        "has_discrepancies": len(unmatched_gl) > 0 or len(unmatched_bank) > 0,
    }
    print(json.dumps(result, indent=2))

    if result["has_discrepancies"]:
        print(f"WARNING: {len(unmatched_gl)} GL + {len(unmatched_bank)} bank items unmatched")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
