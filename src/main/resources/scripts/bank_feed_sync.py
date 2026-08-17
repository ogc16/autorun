#!/usr/bin/env python3
"""
Bank Feed Sync & Reconciliation
Fetches bank statements via API/SFTP, matches transactions against GL entries,
and flags unreconciled items.

Parameters:
  bank_config  : JSON string with bank connection details (optional, uses demo data)
  gl_file      : Path to GL export CSV (optional, generates sample GL entries)
  institution  : Bank name for display (default: Default Bank)
  account      : Account identifier (default: CHECKING-001)
  days         : Days to look back (default: 30)
  tolerance    : Amount matching tolerance in currency units (default: 0.01)
"""
import csv
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone


def parse_args(argv):
    args = {"tolerance": 0.01, "institution": "Default Bank", "account": "CHECKING-001", "days": 30}
    for arg in argv:
        if arg.startswith("bank_config="):
            args["bank_config"] = json.loads(arg.split("=", 1)[1])
        elif arg.startswith("gl_file="):
            args["gl_file"] = arg.split("=", 1)[1]
        elif arg.startswith("institution="):
            args["institution"] = arg.split("=", 1)[1]
        elif arg.startswith("account="):
            args["account"] = arg.split("=", 1)[1]
        elif arg.startswith("days="):
            args["days"] = int(arg.split("=", 1)[1])
        elif arg.startswith("tolerance="):
            args["tolerance"] = float(arg.split("=", 1)[1])
    return args


def generate_demo_bank_txns(institution, account, days):
    """Generate sample bank transactions for demo mode."""
    txns = []
    descriptions = [
        "Wire transfer - Client A", "ACH payment - Vendor B", "POS purchase - Office Supplies",
        "Direct deposit - Payroll", "ATM withdrawal", "Check deposit #1042",
        "Subscription - Cloud Hosting", "Invoice payment received", "Utility bill - Electric",
        "Credit card payment", "Interest earned", "Service fee - Monthly",
    ]
    for i in range(min(days, 12)):
        dt = datetime.now(timezone.utc) - timedelta(days=i)
        amount = round((i + 1) * 127.50 * ((-1) ** i), 2)
        txns.append({
            "id": f"TXN-{account}-{i+1:03d}",
            "date": dt.strftime("%Y-%m-%d"),
            "description": descriptions[i % len(descriptions)],
            "amount": amount,
            "currency": "USD",
            "account": account,
            "bank_id": institution,
        })
    return txns


def generate_demo_gl_entries(bank_txns):
    """Generate GL entries matching some (but not all) bank transactions."""
    entries = []
    for txn in bank_txns:
        entries.append({
            "id": f"GL-{uuid.uuid4().hex[:8]}",
            "date": txn["date"],
            "description": txn["description"],
            "amount": txn["amount"],
            "currency": txn.get("currency", "USD"),
            "reference": txn["id"],
            "matched": False,
        })
    # Add one unmatched GL entry (simulates a manual journal)
    entries.append({
        "id": f"GL-{uuid.uuid4().hex[:8]}",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "description": "Manual journal adjustment",
        "amount": 500.00,
        "currency": "USD",
        "reference": "MJ-001",
        "matched": False,
    })
    return entries


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


def main():
    args = parse_args(sys.argv[1:])
    bank_config = args.get("bank_config")
    gl_file = args.get("gl_file")
    institution = args["institution"]
    account = args["account"]
    tolerance = args["tolerance"]
    days = args["days"]

    # Demo mode: generate sample data if no real bank_config or gl_file
    demo_mode = not bank_config or not gl_file
    if demo_mode:
        bank_txns = generate_demo_bank_txns(institution, account, days)
        gl_entries = generate_demo_gl_entries(bank_txns)
    else:
        gl_entries = load_gl_entries(gl_file)
        bank_txns = simulate_bank_fetch(bank_config)

    matches, unmatched_gl, unmatched_bank = match_transactions(
        gl_entries, bank_txns, tolerance, 72
    )

    result = {
        "status": "success",
        "demo_mode": demo_mode,
        "institution": institution,
        "account": account,
        "period_days": days,
        "summary": {
            "matched": len(matches),
            "unmatched_gl": len(unmatched_gl),
            "unmatched_bank": len(unmatched_bank),
            "total_gl": len(gl_entries),
            "total_bank": len(bank_txns),
            "match_rate_pct": round(len(matches) / max(len(gl_entries), 1) * 100, 1),
        },
        "matches": matches[:5],
        "unmatched_gl": [{"id": e["id"], "date": e["date"], "amount": e["amount"],
                          "description": e["description"]} for e in unmatched_gl[:5]],
        "unmatched_bank": [{"id": t["id"], "date": t["date"], "amount": t["amount"],
                            "description": t["description"]} for t in unmatched_bank[:5]],
        "has_discrepancies": len(unmatched_gl) > 0 or len(unmatched_bank) > 0,
    }
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
