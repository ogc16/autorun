#!/usr/bin/env python3
"""
Dunning & Credit Control
Checks aging AR balances, auto-generates reminder notices, and posts
summary logs for AutoRun execution tracking.

Parameters:
  ar_file      : Path to accounts receivable aging CSV (required)
  aging_buckets : JSON array of bucket day thresholds (default: [30,60,90,120])
  output_dir   : Output directory for dunning letters (default: /tmp/dunning)
  notify       : Send notifications via AutoRun alerts (default: false)
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone


def parse_args(argv):
    args = {
        "aging_buckets": "[30, 60, 90, 120]",
        "output_dir": "/tmp/dunning",
        "notify": "false",
    }
    for arg in argv:
        if arg.startswith("ar_file="):
            args["ar_file"] = arg.split("=", 1)[1]
        elif arg.startswith("aging_buckets="):
            args["aging_buckets"] = arg.split("=", 1)[1]
        elif arg.startswith("output_dir="):
            args["output_dir"] = arg.split("=", 1)[1]
        elif arg.startswith("notify="):
            args["notify"] = arg.split("=", 1)[1].lower()
    return args


def load_ar_balances(filepath):
    entries = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append({
                "customer_id": row.get("customer_id", ""),
                "customer_name": row.get("customer_name", ""),
                "customer_email": row.get("customer_email", ""),
                "invoice_id": row.get("invoice_id", ""),
                "invoice_date": row.get("invoice_date", ""),
                "due_date": row.get("due_date", ""),
                "amount": float(row.get("amount", 0)),
                "currency": row.get("currency", "USD"),
                "days_overdue": int(row.get("days_overdue", 0)),
            })
    return entries


DUNNING_LEVELS = {
    0: {"level": "current", "tone": "friendly", "action": "No action required"},
    30: {"level": "30_days", "tone": "reminder", "action": "First reminder sent"},
    60: {"level": "60_days", "tone": "firm", "action": "Escalation notice sent"},
    90: {"level": "90_days", "tone": "urgent", "action": "Final demand - collections review"},
    120: {"level": "120_days", "tone": "legal", "action": "Referred to legal/collections agency"},
}


def classify_aging(entries, buckets):
    classified = []
    for e in entries:
        days = e["days_overdue"]
        level = 0
        for b in sorted(buckets):
            if days >= b:
                level = b
        dunning = DUNNING_LEVELS.get(level, DUNNING_LEVELS[120])
        classified.append({
            **e,
            "dunning_level": dunning["level"],
            "dunning_tone": dunning["tone"],
            "dunning_action": dunning["action"],
        })
    return classified


def generate_notices(entries, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    notices = []
    by_customer = {}
    for e in entries:
        if e["dunning_level"] == "current":
            continue
        cid = e["customer_id"]
        if cid not in by_customer:
            by_customer[cid] = {
                "customer_id": cid,
                "customer_name": e["customer_name"],
                "customer_email": e["customer_email"],
                "invoices": [],
                "total_overdue": 0,
                "max_days_overdue": 0,
                "dunning_level": e["dunning_level"],
                "dunning_tone": e["dunning_tone"],
            }
        by_customer[cid]["invoices"].append({
            "invoice_id": e["invoice_id"],
            "amount": e["amount"],
            "due_date": e["due_date"],
            "days_overdue": e["days_overdue"],
        })
        by_customer[cid]["total_overdue"] += e["amount"]
        by_customer[cid]["max_days_overdue"] = max(
            by_customer[cid]["max_days_overdue"], e["days_overdue"]
        )

    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    for cid, data in by_customer.items():
        notice = {
            "notice_id": f"DUNN-{cid}-{ts}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "customer": data["customer_name"],
            "email": data["customer_email"],
            "level": data["dunning_level"],
            "tone": data["dunning_tone"],
            "total_overdue": round(data["total_overdue"], 2),
            "oldest_days": data["max_days_overdue"],
            "invoice_count": len(data["invoices"]),
            "invoices": data["invoices"],
        }
        notices.append(notice)

    notices_file = os.path.join(output_dir, f"dunning_notices_{ts}.json")
    with open(notices_file, "w") as f:
        json.dump(notices, f, indent=2)

    return notices_file, notices


def main():
    args = parse_args(sys.argv[1:])
    ar_file = args.get("ar_file")

    if not ar_file:
        print("ERROR: ar_file parameter is required (path to AR aging CSV)")
        sys.exit(1)

    buckets = json.loads(args["aging_buckets"])
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting dunning & credit control run...")
    print(f"Aging buckets: {buckets}")

    entries = load_ar_balances(ar_file)
    print(f"Loaded {len(entries)} AR invoice entries")

    classified = classify_aging(entries, buckets)

    overdue = [e for e in classified if e["dunning_level"] != "current"]
    current = [e for e in classified if e["dunning_level"] == "current"]
    total_overdue = sum(e["amount"] for e in overdue)

    print(f"Current: {len(current)}, Overdue: {len(overdue)}, Total overdue: {total_overdue:,.2f}")

    by_level = {}
    for e in overdue:
        lvl = e["dunning_level"]
        by_level[lvl] = by_level.get(lvl, {"count": 0, "total": 0})
        by_level[lvl]["count"] += 1
        by_level[lvl]["total"] += e["amount"]

    for lvl, data in sorted(by_level.items()):
        print(f"  {lvl}: {data['count']} invoices, ${data['total']:,.2f}")

    notices_file, notices = generate_notices(overdue, args["output_dir"])
    print(f"Generated {len(notices)} dunning notices")

    result = {
        "status": "success",
        "total_invoices": len(entries),
        "current_count": len(current),
        "overdue_count": len(overdue),
        "total_overdue_amount": round(total_overdue, 2),
        "notices_generated": len(notices),
        "notices_file": notices_file,
        "by_level": {k: {"count": v["count"], "total": round(v["total"], 2)}
                     for k, v in by_level.items()},
    }
    print(json.dumps(result, indent=2))

    critical = [e for e in overdue if e["days_overdue"] >= 90]
    if critical:
        print(f"WARNING: {len(critical)} invoices 90+ days overdue — collections review needed")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
