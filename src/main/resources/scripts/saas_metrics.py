#!/usr/bin/env python3
"""
SaaS Metrics & Unit Economics
Calculates MRR, ARR, churn, LTV, CAC, NDR, and cohort retention
from subscription and revenue data.

Parameters:
  period        : Reporting period YYYY-MM (default: current month)
  cohort_months : Months for cohort analysis (default: 12)
  churn_window  : Days to look for churn signals (default: 90)
"""
import json
import os
import sys
from datetime import datetime


def parse_args(argv):
    now = datetime.now()
    args = {
        "period": now.strftime("%Y-%m"),
        "cohort_months": 12,
        "churn_window": 90,
    }
    for arg in argv:
        if arg.startswith("period="):
            args["period"] = arg.split("=", 1)[1]
        elif arg.startswith("cohort_months="):
            args["cohort_months"] = int(arg.split("=", 1)[1])
        elif arg.startswith("churn_window="):
            args["churn_window"] = int(arg.split("=", 1)[1])
    return args


def generate_demo_data(period, cohort_months):
    customers = [
        {"id": 1, "plan": "Enterprise", "mrr": 8500, "seats": 50, "tenure_months": 24, "status": "active"},
        {"id": 2, "plan": "Enterprise", "mrr": 6200, "seats": 30, "tenure_months": 18, "status": "active"},
        {"id": 3, "plan": "Pro", "mrr": 2400, "seats": 12, "tenure_months": 15, "status": "active"},
        {"id": 4, "plan": "Pro", "mrr": 1800, "seats": 8, "tenure_months": 9, "status": "active"},
        {"id": 5, "plan": "Pro", "mrr": 990, "seats": 5, "tenure_months": 6, "status": "active"},
        {"id": 6, "plan": "Starter", "mrr": 490, "seats": 3, "tenure_months": 3, "status": "active"},
        {"id": 7, "plan": "Starter", "mrr": 290, "seats": 2, "tenure_months": 2, "status": "active"},
        {"id": 8, "plan": "Enterprise", "mrr": 0, "seats": 0, "tenure_months": 12, "status": "churned", "churn_date": "2026-07-15"},
        {"id": 9, "plan": "Pro", "mrr": 0, "seats": 0, "tenure_months": 8, "status": "churned", "churn_date": "2026-06-20"},
        {"id": 10, "plan": "Starter", "mrr": 0, "seats": 0, "tenure_months": 4, "status": "churned", "churn_date": "2026-05-10"},
    ]
    revenue_history = []
    base = 15000
    for i in range(cohort_months):
        m = datetime.now().month - i
        y = datetime.now().year
        while m <= 0:
            m += 12
            y -= 1
        rev = base * (1 + 0.05 * (cohort_months - i))
        revenue_history.append({
            "month": f"{y}-{m:02d}",
            "mrr": round(rev, 2),
            "new_mrr": round(rev * 0.08, 2),
            "churned_mrr": round(rev * 0.03, 2),
            "expansion_mrr": round(rev * 0.04, 2),
        })
    revenue_history.reverse()
    return customers, revenue_history


def calculate_cohort_retention(customers, cohort_months):
    cohorts = {}
    for c in customers:
        tm = c["tenure_months"]
        bucket = min(tm, cohort_months)
        cohorts[bucket] = cohorts.get(bucket, 0) + 1
    total = len(customers)
    retention = []
    for m in range(1, cohort_months + 1):
        alive = sum(1 for c in customers if c["tenure_months"] >= m)
        retention.append({
            "month": m,
            "retained_pct": round(alive / total * 100, 1) if total else 0,
            "count": alive,
        })
    return retention


def main():
    args = parse_args(sys.argv[1:])
    period = args["period"]
    cohort_months = args["cohort_months"]
    churn_window = args["churn_window"]

    customers, revenue_history = generate_demo_data(period, cohort_months)
    active = [c for c in customers if c["status"] == "active"]
    churned = [c for c in customers if c["status"] == "churned"]

    mrr = sum(c["mrr"] for c in active)
    arr = mrr * 12
    avg_revenue_per_account = mrr / len(active) if active else 0
    total_seats = sum(c["seats"] for c in active)
    arpu = mrr / total_seats if total_seats else 0

    gross_churn_rate = len(churned) / len(customers) * 100 if customers else 0
    revenue_churn_mrr = sum(c.get("mrr", 0) for c in churned if "mrr" in c)
    net_churn_rate = revenue_churn_mrr / mrr * 100 if mrr else 0

    avg_lifespan_months = 100 / gross_churn_rate if gross_churn_rate > 0 else 999
    ltv = avg_revenue_per_account * avg_lifespan_months
    cac_est = avg_revenue_per_account * 3.2
    ltv_cac_ratio = ltv / cac_est if cac_est else 0

    avg_tenure = sum(c["tenure_months"] for c in customers) / len(customers) if customers else 0
    avg_seats = total_seats / len(active) if active else 0

    plan_breakdown = {}
    for c in active:
        p = c["plan"]
        if p not in plan_breakdown:
            plan_breakdown[p] = {"count": 0, "mrr": 0, "seats": 0}
        plan_breakdown[p]["count"] += 1
        plan_breakdown[p]["mrr"] += c["mrr"]
        plan_breakdown[p]["seats"] += c["seats"]
    for p in plan_breakdown:
        plan_breakdown[p]["mrr"] = round(plan_breakdown[p]["mrr"], 2)
        plan_breakdown[p]["share_pct"] = round(plan_breakdown[p]["mrr"] / mrr * 100, 1) if mrr else 0

    cohort = calculate_cohort_retention(customers, cohort_months)
    nrr = (mrr + sum(c.get("mrr", 0) for c in active if c["tenure_months"] > 6)) / mrr * 100 if mrr else 0

    result = {
        "period": period,
        "summary": {
            "mrr": round(mrr, 2),
            "arr": round(arr, 2),
            "active_customers": len(active),
            "churned_customers": len(churned),
            "total_seats": total_seats,
            "arpu": round(arpu, 2),
            "arpa": round(avg_revenue_per_account, 2),
        },
        "unit_economics": {
            "ltv": round(ltv, 2),
            "estimated_cac": round(cac_est, 2),
            "ltv_cac_ratio": round(ltv_cac_ratio, 2),
            "avg_lifespan_months": round(avg_lifespan_months, 1),
            "avg_tenure_months": round(avg_tenure, 1),
            "avg_seats_per_account": round(avg_seats, 1),
        },
        "churn": {
            "gross_churn_rate_pct": round(gross_churn_rate, 2),
            "net_revenue_churn_pct": round(net_churn_rate, 2),
            "net_revenue_retention_pct": round(100 - net_churn_rate, 2),
        },
        "plan_breakdown": plan_breakdown,
        "cohort_retention": cohort,
        "revenue_history": revenue_history,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
