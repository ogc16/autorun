#!/usr/bin/env python3
"""
Depreciation & Amortization Run
Triggers asset schedule recalculations and posts monthly depreciation journals
via ERP APIs (SAP, NetSuite, Xero, or local CSV).

Parameters:
  asset_file   : Path to asset register CSV (required)
  method       : Depreciation method: straight_line, declining_balance, sum_of_years (default: straight_line)
  useful_life  : Default useful life in months if not in asset file (default: 60)
  salvage_pct   : Salvage value as percentage of cost (default: 10)
  period       : Accounting period YYYY-MM (default: current month)
  output_dir   : Output directory (default: /tmp/depreciation)
  erp_api      : ERP endpoint URL for posting (optional, demo only)
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone


def parse_args(argv):
    now = datetime.now(timezone.utc)
    args = {
        "method": "straight_line",
        "useful_life": 60,
        "salvage_pct": 10.0,
        "period": f"{now.year}-{now.month:02d}",
        "output_dir": "/tmp/depreciation",
        "erp_api": "",
    }
    for arg in argv:
        if arg.startswith("asset_file="):
            args["asset_file"] = arg.split("=", 1)[1]
        elif arg.startswith("method="):
            args["method"] = arg.split("=", 1)[1]
        elif arg.startswith("useful_life="):
            args["useful_life"] = int(arg.split("=", 1)[1])
        elif arg.startswith("salvage_pct="):
            args["salvage_pct"] = float(arg.split("=", 1)[1])
        elif arg.startswith("period="):
            args["period"] = arg.split("=", 1)[1]
        elif arg.startswith("output_dir="):
            args["output_dir"] = arg.split("=", 1)[1]
        elif arg.startswith("erp_api="):
            args["erp_api"] = arg.split("=", 1)[1]
    return args


def load_assets(filepath):
    assets = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assets.append({
                "asset_id": row.get("asset_id", ""),
                "name": row.get("name", ""),
                "category": row.get("category", ""),
                "cost": float(row.get("cost", 0)),
                "accumulated_depr": float(row.get("accumulated_depreciation", 0)),
                "useful_life_months": int(row.get("useful_life_months", 0)),
                "salvage_value": float(row.get("salvage_value", 0)),
                "acquisition_date": row.get("acquisition_date", ""),
                "depr_method": row.get("depr_method", ""),
            })
    return assets


def calc_straight_line(cost, salvage, useful_life):
    if useful_life <= 0:
        return 0
    return round((cost - salvage) / useful_life, 2)


def calc_declining_balance(cost, accum, salvage, useful_life):
    if useful_life <= 0:
        return 0
    book_value = cost - accum
    rate = 2.0 / useful_life
    depr = round(max(0, (book_value - salvage) * rate), 2)
    return depr


def calc_sum_of_years(cost, salvage, useful_life):
    if useful_life <= 0:
        return 0
    depreciable = cost - salvage
    sum_years = useful_life * (useful_life + 1) / 2
    return round(depreciable / sum_years, 2)


def calculate_depreciation(assets, args):
    journals = []
    total_depr = 0

    for asset in assets:
        cost = asset["cost"]
        accum = asset["accumulated_depr"]
        useful_life = asset["useful_life_months"] or args["useful_life"]
        salvage = asset["salvage_value"] or round(cost * args["salvage_pct"] / 100, 2)
        method = asset["depr_method"] or args["method"]

        remaining = cost - accum - salvage
        if remaining <= 0:
            continue

        if method == "declining_balance":
            monthly = calc_declining_balance(cost, accum, salvage, useful_life)
        elif method == "sum_of_years":
            monthly = calc_sum_of_years(cost, salvage, useful_life)
        else:
            monthly = calc_straight_line(cost, salvage, useful_life)

        monthly = min(monthly, remaining)

        if monthly > 0:
            journals.append({
                "asset_id": asset["asset_id"],
                "asset_name": asset["name"],
                "category": asset["category"],
                "method": method,
                "cost": cost,
                "accumulated_before": accum,
                "depreciation_expense": monthly,
                "accumulated_after": round(accum + monthly, 2),
                "book_value_after": round(cost - accum - monthly, 2),
                "salvage_value": salvage,
                "useful_life_months": useful_life,
            })
            total_depr += monthly

    return journals, round(total_depr, 2)


def write_output(output_dir, period, journals, total_depr):
    os.makedirs(output_dir, exist_ok=True)

    journal_file = os.path.join(output_dir, f"depreciation_{period}.json")
    with open(journal_file, "w") as f:
        json.dump({
            "period": period,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_depreciation": total_depr,
            "asset_count": len(journals),
            "journals": journals,
        }, f, indent=2)

    summary_file = os.path.join(output_dir, f"depreciation_summary_{period}.csv")
    with open(summary_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "asset_id", "asset_name", "category", "method", "cost",
            "accumulated_before", "depreciation_expense", "accumulated_after",
            "book_value_after", "salvage_value",
        ])
        writer.writeheader()
        writer.writerows(journals)

    return journal_file, summary_file


def main():
    args = parse_args(sys.argv[1:])
    asset_file = args.get("asset_file")

    if not asset_file:
        print("ERROR: asset_file parameter is required (path to asset register CSV)")
        sys.exit(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting depreciation run for {args['period']}...")
    print(f"Method: {args['method']}, Useful life: {args['useful_life']}mo, Salvage: {args['salvage_pct']}%")

    assets = load_assets(asset_file)
    print(f"Loaded {len(assets)} assets")

    journals, total_depr = calculate_depreciation(assets, args)
    print(f"Calculated depreciation for {len(journals)} assets, total: {total_depr}")

    journal_file, summary_file = write_output(args["output_dir"], args["period"], journals, total_depr)

    result = {
        "status": "success",
        "period": args["period"],
        "method": args["method"],
        "total_depreciation": total_depr,
        "assets_depreciated": len(journals),
        "assets_fully_depreciated": len(assets) - len(journals),
        "journal_file": journal_file,
        "summary_file": summary_file,
    }
    if args["erp_api"]:
        result["erp_api"] = args["erp_api"]
        result["erp_posted"] = False
        result["note"] = "ERP posting simulated — connect to real API in production"

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
