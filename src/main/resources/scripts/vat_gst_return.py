#!/usr/bin/env python3
"""
VAT/GST Return Pre-compilation
Aggregates tax ledgers into standardized VAT returns, runs validation
checks, and outputs alerts on discrepancies.

Parameters:
  tax_file     : Path to tax ledger CSV (required)
  country      : Country code: GB, IE, DE, AU, NZ, SG (default: GB)
  period       : Tax period YYYY-QN or YYYY-MM (default: current quarter)
  output_dir   : Output directory (default: /tmp/vat_return)
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone


def parse_args(argv):
    now = datetime.now(timezone.utc)
    q = (now.month - 1) // 3 + 1
    args = {
        "country": "GB",
        "period": f"{now.year}-Q{q}",
        "output_dir": "/tmp/vat_return",
    }
    for arg in argv:
        if arg.startswith("tax_file="):
            args["tax_file"] = arg.split("=", 1)[1]
        elif arg.startswith("country="):
            args["country"] = arg.split("=", 1)[1].upper()
        elif arg.startswith("period="):
            args["period"] = arg.split("=", 1)[1]
        elif arg.startswith("output_dir="):
            args["output_dir"] = arg.split("=", 1)[1]
    return args


def load_tax_ledger(filepath):
    entries = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append({
                "transaction_id": row.get("transaction_id", ""),
                "date": row.get("date", ""),
                "type": row.get("type", "sale"),
                "vat_category": row.get("vat_category", "standard"),
                "net_amount": float(row.get("net_amount", 0)),
                "vat_amount": float(row.get("vat_amount", 0)),
                "gross_amount": float(row.get("gross_amount", 0)),
                "vat_rate": float(row.get("vat_rate", 20.0)),
                "counterparty": row.get("counterparty", ""),
                "reclaimable": row.get("reclaimable", "true").lower() == "true",
            })
    return entries


VAT_RATES = {
    "GB": {"standard": 20.0, "reduced": 5.0, "zero": 0.0},
    "IE": {"standard": 23.0, "reduced": 13.0, "zero": 0.0},
    "DE": {"standard": 19.0, "reduced": 7.0, "zero": 0.0},
    "AU": {"standard": 10.0, "reduced": 0.0, "zero": 0.0},
    "NZ": {"standard": 15.0, "reduced": 0.0, "zero": 0.0},
    "SG": {"standard": 9.0, "reduced": 0.0, "zero": 0.0},
}


def compile_return(entries, country):
    rates = VAT_RATES.get(country, VAT_RATES["GB"])
    output_supplies = {"standard": 0, "reduced": 0, "zero": 0}
    output_vat = {"standard": 0, "reduced": 0, "zero": 0}
    input_supplies = {"standard": 0, "reduced": 0, "zero": 0}
    input_vat = {"standard": 0, "reduced": 0, "zero": 0}
    discrepancies = []
    validation_errors = []

    for e in entries:
        cat = e["vat_category"]
        expected_rate = rates.get(cat, rates["standard"])
        expected_vat = round(e["net_amount"] * expected_rate / 100, 2)
        actual_diff = abs(e["vat_amount"] - expected_vat)

        if actual_diff > 0.02:
            discrepancies.append({
                "transaction_id": e["transaction_id"],
                "date": e["date"],
                "net": e["net_amount"],
                "expected_vat": expected_vat,
                "actual_vat": e["vat_amount"],
                "difference": round(actual_diff, 2),
            })

        gross_check = round(e["net_amount"] + e["vat_amount"], 2)
        if abs(gross_check - e["gross_amount"]) > 0.02:
            validation_errors.append({
                "transaction_id": e["transaction_id"],
                "error": f"Gross mismatch: net+vat={gross_check} vs gross={e['gross_amount']}",
            })

        if e["type"] == "sale":
            output_supplies[cat] = output_supplies.get(cat, 0) + e["net_amount"]
            output_vat[cat] = output_vat.get(cat, 0) + e["vat_amount"]
        else:
            input_supplies[cat] = input_supplies.get(cat, 0) + e["net_amount"]
            input_vat[cat] = input_vat.get(cat, 0) + e["vat_amount"]

    total_output_vat = round(sum(output_vat.values()), 2)
    total_input_vat = round(sum(input_vat.values()), 2)
    net_vat = round(total_output_vat - total_input_vat, 2)

    return {
        "country": country,
        "rates": rates,
        "boxes": {
            "box_1_output_vat": total_output_vat,
            "box_2_eu_acquisitions_vat": 0,
            "box_3_total_output": round(sum(output_supplies.values()), 2),
            "box_4_input_vat": total_input_vat,
            "box_5_net_vat": net_vat,
            "box_6_total_value_sales": round(sum(output_supplies.values()), 2),
            "box_7_total_value_purchases": round(sum(input_supplies.values()), 2),
            "box_8_eu_sales": 0,
            "box_9_eu_purchases": 0,
        },
        "by_category": {
            "output_supplies": output_supplies,
            "output_vat": output_vat,
            "input_supplies": input_supplies,
            "input_vat": input_vat,
        },
        "transaction_count": len(entries),
        "discrepancies": discrepancies,
        "validation_errors": validation_errors,
    }


def write_output(output_dir, period, return_data):
    os.makedirs(output_dir, exist_ok=True)
    report_file = os.path.join(output_dir, f"vat_return_{period}.json")
    with open(report_file, "w") as f:
        json.dump(return_data, f, indent=2)
    return report_file


def main():
    args = parse_args(sys.argv[1:])
    tax_file = args.get("tax_file")

    if not tax_file:
        print("ERROR: tax_file parameter is required (path to tax ledger CSV)")
        sys.exit(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting VAT/GST return compilation...")
    print(f"Country: {args['country']}, Period: {args['period']}")

    entries = load_tax_ledger(tax_file)
    print(f"Loaded {len(entries)} tax ledger entries")

    return_data = compile_return(entries, args["country"])
    report_file = write_output(args["output_dir"], args["period"], return_data)

    result = {
        "status": "success",
        "period": args["period"],
        "country": args["country"],
        "report_file": report_file,
        "net_vat_payable": return_data["boxes"]["box_5_net_vat"],
        "discrepancies": len(return_data["discrepancies"]),
        "validation_errors": len(return_data["validation_errors"]),
    }
    print(json.dumps(result, indent=2))

    if return_data["discrepancies"] or return_data["validation_errors"]:
        print(f"WARNING: {len(return_data['discrepancies'])} discrepancies, "
              f"{len(return_data['validation_errors'])} validation errors found")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
