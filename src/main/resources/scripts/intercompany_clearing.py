#!/usr/bin/env python3
"""
Intercompany Clearing & Elimination
Automated cross-entity ledger matching to generate elimination journal entries
for end-of-month consolidation.

Parameters:
  entities    : JSON array of entity ledger CSV paths (required)
  period      : Accounting period YYYY-MM (default: current month)
  tolerance   : Amount matching tolerance (default: 0.01)
  output_dir  : Output directory for elimination entries (default: /tmp/intercompany)
"""
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone


def parse_args(argv):
    now = datetime.now(timezone.utc)
    args = {
        "period": f"{now.year}-{now.month:02d}",
        "tolerance": 0.01,
        "output_dir": "/tmp/intercompany",
    }
    for arg in argv:
        if arg.startswith("entities="):
            args["entities"] = json.loads(arg.split("=", 1)[1])
        elif arg.startswith("period="):
            args["period"] = arg.split("=", 1)[1]
        elif arg.startswith("tolerance="):
            args["tolerance"] = float(arg.split("=", 1)[1])
        elif arg.startswith("output_dir="):
            args["output_dir"] = arg.split("=", 1)[1]
    return args


def load_entity_ledger(filepath):
    entries = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append({
                "entity": row.get("entity", os.path.basename(filepath)),
                "counterparty": row.get("counterparty", ""),
                "date": row.get("date", ""),
                "description": row.get("description", ""),
                "debit": float(row.get("debit", 0)),
                "credit": float(row.get("credit", 0)),
                "reference": row.get("reference", ""),
                "matched": False,
            })
    return entries


def find_intercompany_pairs(all_entries, tolerance):
    pairs = []
    unmatched = []

    by_counterparty = defaultdict(list)
    for e in all_entries:
        if e["counterparty"]:
            by_counterparty[(e["entity"], e["counterparty"])].append(e)

    matched_indices = set()
    for key, entries_a in by_counterparty.items():
        entity_a, counterparty_a = key
        reverse_key = (counterparty_a, entity_a)
        entries_b = by_counterparty.get(reverse_key, [])

        for ea in entries_a:
            if id(ea) in matched_indices:
                continue
            for eb in entries_b:
                if id(eb) in matched_indices:
                    continue
                if ea["entity"] == eb["counterparty"] and ea["counterparty"] == eb["entity"]:
                    net_a = ea["debit"] - ea["credit"]
                    net_b = eb["debit"] - eb["credit"]
                    if abs(net_a + net_b) <= tolerance:
                        pairs.append({
                            "entity_a": ea["entity"],
                            "entity_b": eb["entity"],
                            "amount_a": net_a,
                            "amount_b": net_b,
                            "reference_a": ea["reference"],
                            "reference_b": eb["reference"],
                            "description": f"IC elimination: {ea['entity']} <-> {eb['entity']}",
                        })
                        ea["matched"] = True
                        eb["matched"] = True
                        matched_indices.add(id(ea))
                        matched_indices.add(id(eb))
                        break

    for e in all_entries:
        if id(e) not in matched_indices:
            unmatched.append(e)

    return pairs, unmatched


def generate_elimination_journals(pairs, period):
    journals = []
    for i, pair in enumerate(pairs, 1):
        journals.append({
            "journal_id": f"ELIM-{period}-{i:04d}",
            "period": period,
            "date": f"{period}-28",
            "entity_a": pair["entity_a"],
            "entity_b": pair["entity_b"],
            "debit_entity": pair["entity_a"],
            "credit_entity": pair["entity_b"],
            "amount": abs(pair["amount_a"]),
            "description": pair["description"],
            "reference_a": pair["reference_a"],
            "reference_b": pair["reference_b"],
            "type": "intercompany_elimination",
        })
    return journals


def write_output(output_dir, period, journals, unmatched):
    os.makedirs(output_dir, exist_ok=True)

    journal_file = os.path.join(output_dir, f"elimination_journals_{period}.json")
    with open(journal_file, "w") as f:
        json.dump(journals, f, indent=2)

    if unmatched:
        unmatched_file = os.path.join(output_dir, f"unmatched_{period}.json")
        with open(unmatched_file, "w") as f:
            json.dump([{
                "entity": e["entity"], "counterparty": e["counterparty"],
                "amount": e["debit"] - e["credit"], "reference": e["reference"],
                "description": e["description"],
            } for e in unmatched], f, indent=2)
    else:
        unmatched_file = None

    return journal_file, unmatched_file


def main():
    args = parse_args(sys.argv[1:])
    entities = args.get("entities")

    if not entities:
        print("ERROR: entities parameter is required (JSON array of CSV paths)")
        sys.exit(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting intercompany clearing for {args['period']}...")

    all_entries = []
    for path in entities:
        entries = load_entity_ledger(path)
        all_entries.extend(entries)
        print(f"Loaded {len(entries)} entries from {path}")

    pairs, unmatched = find_intercompany_pairs(all_entries, args["tolerance"])
    print(f"Found {len(pairs)} intercompany pairs, {len(unmatched)} unmatched entries")

    journals = generate_elimination_journals(pairs, args["period"])
    journal_file, unmatched_file = write_output(args["output_dir"], journals, unmatched)

    result = {
        "status": "success",
        "period": args["period"],
        "elimination_journals": journal_file,
        "summary": {
            "pairs_matched": len(pairs),
            "journals_generated": len(journals),
            "unmatched_entries": len(unmatched),
        },
    }
    if unmatched_file:
        result["unmatched_file"] = unmatched_file

    print(json.dumps(result, indent=2))
    sys.exit(0 if len(unmatched) == 0 else 1)


if __name__ == "__main__":
    main()
