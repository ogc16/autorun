#!/usr/bin/env python3
"""
Budget vs. Actuals Variance Analysis
Compares actual GL balances against approved budgets by cost centre and account,
flagging material variances for management review.

Parameters:
  period          : Reporting period YYYY-MM (default: current month)
  threshold_pct   : Flag variances exceeding this percentage (default: 10)
  by_cost_center  : Break down by cost centre (default: true)
"""
import json
import os
import sys
from datetime import datetime


def parse_args(argv):
    now = datetime.now()
    args = {
        "period": now.strftime("%Y-%m"),
        "threshold_pct": 10.0,
        "by_cost_center": True,
    }
    for arg in argv:
        if arg.startswith("period="):
            args["period"] = arg.split("=", 1)[1]
        elif arg.startswith("threshold_pct="):
            args["threshold_pct"] = float(arg.split("=", 1)[1])
        elif arg.startswith("by_cost_center="):
            args["by_cost_center"] = arg.split("=", 1)[1].lower() == "true"
    return args


def load_data(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_demo_budget():
    accounts = [
        {"code": "4000", "name": "Revenue - SaaS", "budget": 500000, "actual": 532000, "cost_centre": "Sales"},
        {"code": "4100", "name": "Revenue - Services", "budget": 120000, "actual": 108000, "cost_centre": "Consulting"},
        {"code": "5000", "name": "COGS - Hosting", "budget": 80000, "actual": 87500, "cost_centre": "Engineering"},
        {"code": "5100", "name": "COGS - Licenses", "budget": 25000, "actual": 24800, "cost_centre": "Engineering"},
        {"code": "6000", "name": "R&D Salaries", "budget": 320000, "actual": 335000, "cost_centre": "Engineering"},
        {"code": "6100", "name": "R&D Tools & SaaS", "budget": 45000, "actual": 52000, "cost_centre": "Engineering"},
        {"code": "7000", "name": "Sales & Marketing", "budget": 95000, "actual": 110000, "cost_centre": "Marketing"},
        {"code": "7100", "name": "G&A Salaries", "budget": 150000, "actual": 148000, "cost_centre": "Finance"},
        {"code": "7200", "name": "G&A Travel", "budget": 15000, "actual": 22000, "cost_centre": "Finance"},
        {"code": "7300", "name": "G&A Professional Fees", "budget": 30000, "actual": 28000, "cost_centre": "Finance"},
    ]
    return accounts


def variance_pct(budget, actual):
    if budget == 0:
        return 0.0 if actual == 0 else 999.99
    return round(((actual - budget) / abs(budget)) * 100, 2)


def status(v_pct, threshold):
    if abs(v_pct) > threshold:
        return "FLAGGED"
    return "OK"


def main():
    args = parse_args(sys.argv[1:])
    period = args["period"]
    threshold = args["threshold_pct"]
    by_cc = args["by_cost_center"]

    demo_path = os.path.join(os.path.dirname(__file__), "data", "bva_data.json")
    accounts = load_data(demo_path)
    if not accounts:
        accounts = generate_demo_budget()

    items = []
    total_budget = 0
    total_actual = 0
    flagged_count = 0
    by_centre = {}

    for acct in accounts:
        v_pct = variance_pct(acct["budget"], acct["actual"])
        st = status(v_pct, threshold)
        if st == "FLAGGED":
            flagged_count += 1
        total_budget += acct["budget"]
        total_actual += acct["actual"]
        item = {
            "account_code": acct["code"],
            "account_name": acct["name"],
            "cost_centre": acct.get("cost_centre", "Unallocated"),
            "budget": acct["budget"],
            "actual": acct["actual"],
            "variance_abs": acct["actual"] - acct["budget"],
            "variance_pct": v_pct,
            "status": st,
        }
        items.append(item)
        if by_cc:
            cc = acct.get("cost_centre", "Unallocated")
            if cc not in by_centre:
                by_centre[cc] = {"budget": 0, "actual": 0, "items": 0, "flagged": 0}
            by_centre[cc]["budget"] += acct["budget"]
            by_centre[cc]["actual"] += acct["actual"]
            by_centre[cc]["items"] += 1
            if st == "FLAGGED":
                by_centre[cc]["flagged"] += 1

    total_v_pct = variance_pct(total_budget, total_actual)

    cost_centre_summary = []
    for cc, vals in sorted(by_centre.items()):
        cost_centre_summary.append({
            "cost_centre": cc,
            "budget": vals["budget"],
            "actual": vals["actual"],
            "variance_abs": vals["actual"] - vals["budget"],
            "variance_pct": variance_pct(vals["budget"], vals["actual"]),
            "account_count": vals["items"],
            "flagged_count": vals["flagged"],
        })

    result = {
        "period": period,
        "threshold_pct": threshold,
        "summary": {
            "total_budget": total_budget,
            "total_actual": total_actual,
            "total_variance_abs": total_actual - total_budget,
            "total_variance_pct": total_v_pct,
            "accounts_analysed": len(accounts),
            "flagged_count": flagged_count,
        },
        "cost_centre_summary": cost_centre_summary if by_cc else [],
        "variances": sorted(items, key=lambda x: abs(x["variance_pct"]), reverse=True),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
