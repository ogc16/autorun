#!/usr/bin/env python3
"""
Board Pack & KPI Narrative Generator
Assembles financial statements, KPIs, and variance data into a structured
board-ready narrative with executive summary, P&L, balance sheet, and forecasts.

Parameters:
  period   : Reporting period YYYY-MM (default: current month)
  sections : Comma-separated sections to include (default: all)
  format   : json, html, text (default: json)
  audience : board, cfo, investors (default: board)
"""
import json
import os
import sys
from datetime import datetime


def parse_args(argv):
    now = datetime.now()
    args = {
        "period": now.strftime("%Y-%m"),
        "sections": "all",
        "format": "json",
        "audience": "board",
    }
    for arg in argv:
        if arg.startswith("period="):
            args["period"] = arg.split("=", 1)[1]
        elif arg.startswith("sections="):
            args["sections"] = arg.split("=", 1)[1]
        elif arg.startswith("format="):
            args["format"] = arg.split("=", 1)[1]
        elif arg.startswith("audience="):
            args["audience"] = arg.split("=", 1)[1]
    return args


def generate_demo_data(period):
    return {
        "kpi_summary": {
            "mrr": 20680,
            "arr": 248160,
            "mrr_growth_pct": 4.2,
            "gross_margin_pct": 62.8,
            "net_income": 89200,
            "cash_runway_months": 18,
            "nrr_pct": 108.5,
            "ltv_cac_ratio": 4.2,
            "headcount": 42,
            "revenue_per_employee": 5909,
        },
        "p_and_l": {
            "revenue": {
                "saas_subscriptions": 485000,
                "professional_services": 108000,
                "total_revenue": 593000,
            },
            "cost_of_revenue": {
                "hosting_and_infra": 87500,
                "software_licenses": 24800,
                "customer_support": 42000,
                "total_cogs": 154300,
            },
            "gross_profit": 438700,
            "operating_expenses": {
                "research_and_development": 175000,
                "sales_and_marketing": 110000,
                "general_and_administrative": 64500,
                "total_opex": 349500,
            },
            "operating_income": 89200,
            "net_income": 89200,
        },
        "balance_sheet": {
            "assets": {
                "cash_and_equivalents": 1340000,
                "accounts_receivable": 165000,
                "prepaid_expenses": 32000,
                "total_current_assets": 1537000,
                "fixed_assets_net": 45000,
                "total_assets": 1582000,
            },
            "liabilities": {
                "accounts_payable": 78000,
                "accrued_expenses": 52000,
                "deferred_revenue": 125000,
                "total_current_liabilities": 255000,
                "total_liabilities": 255000,
            },
            "equity": {
                "share_capital": 500000,
                "retained_earnings": 827000,
                "total_equity": 1327000,
            },
        },
        "cashflow": {
            "operating": 142000,
            "investing": -35000,
            "financing": -12000,
            "net_change": 95000,
            "beginning_cash": 1245000,
            "ending_cash": 1340000,
        },
        "variances": [
            {"line": "Revenue", "budget": 570000, "actual": 593000, "variance_pct": 4.0, "comment": "Strong SaaS upsell activity"},
            {"line": "Hosting", "budget": 80000, "actual": 87500, "variance_pct": 9.4, "comment": "Usage exceeded forecast"},
            {"line": "S&M", "budget": 95000, "actual": 110000, "variance_pct": 15.8, "comment": "Q3 campaign spend pull-forward"},
            {"line": "G&A Travel", "budget": 15000, "actual": 22000, "variance_pct": 46.7, "comment": "Board offsite and conference travel"},
        ],
        "forecasts": {
            "q3_revenue_estimate": 620000,
            "q4_revenue_estimate": 655000,
            "fy_revenue_estimate": 2380000,
            "fy_arr_target": 2600000,
        },
    }


def build_narrative(data, audience):
    kpi = data.get("kpi_summary", {})
    pl = data.get("p_and_l", {})
    bs = data.get("balance_sheet", {})
    cf = data.get("cashflow", {})
    fc = data.get("forecasts", {})

    tone = "formal" if audience == "board" else "technical" if audience == "cfo" else "growth-focused"
    sections = []

    sections.append({
        "title": "Executive Summary",
        "content": (
            f"Total revenue for the period was ${pl.get('revenue', {}).get('total_revenue', 0):,.0f}, "
            f"driven by ${pl.get('revenue', {}).get('saas_subscriptions', 0):,.0f} in SaaS subscriptions "
            f"and ${pl.get('revenue', {}).get('professional_services', 0):,.0f} in professional services. "
            f"Gross margin stood at {kpi.get('gross_margin_pct', 0)}%, with MRR growth of "
            f"{kpi.get('mrr_growth_pct', 0)}% month-over-month. "
            f"Net income for the period was ${pl.get('net_income', 0):,.0f}. "
            f"Cash runway stands at {kpi.get('cash_runway_months', 0)} months with "
            f"${bs.get('assets', {}).get('cash_and_equivalents', 0):,.0f} on hand."
        ),
    })

    sections.append({
        "title": "Key Performance Indicators",
        "metrics": kpi,
    })

    sections.append({
        "title": "Profit & Loss",
        "detail": pl,
    })

    sections.append({
        "title": "Balance Sheet",
        "detail": bs,
    })

    sections.append({
        "title": "Cash Flow Statement",
        "detail": cf,
    })

    if data.get("variances"):
        variance_lines = []
        for v in data["variances"]:
            direction = "over" if v["variance_pct"] > 0 else "under"
            variance_lines.append(
                f"{v['line']}: {abs(v['variance_pct']):.1f}% {direction} budget — {v.get('comment', 'No comment')}"
            )
        sections.append({
            "title": "Key Variances",
            "content": "\n".join(variance_lines),
        })

    if fc:
        sections.append({
            "title": "Forward Outlook",
            "content": (
                f"Q3 revenue estimate: ${fc.get('q3_revenue_estimate', 0):,.0f}. "
                f"Q4 revenue estimate: ${fc.get('q4_revenue_estimate', 0):,.0f}. "
                f"Full-year revenue estimate: ${fc.get('fy_revenue_estimate', 0):,.0f} "
                f"(ARR target: ${fc.get('fy_arr_target', 0):,.0f})."
            ),
        })

    return {
        "period": data.get("period", ""),
        "audience": audience,
        "tone": tone,
        "generated_at": datetime.now().isoformat(),
        "sections": sections,
    }


def main():
    args = parse_args(sys.argv[1:])
    period = args["period"]
    requested_sections = args["sections"].lower().split(",") if args["sections"] != "all" else ["all"]
    audience = args["audience"]
    output_format = args["format"]

    demo_path = os.path.join(os.path.dirname(__file__), "data", "board_deck.json")
    data = None
    if os.path.exists(demo_path):
        with open(demo_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    if not data:
        data = generate_demo_data(period)
    data["period"] = period

    narrative = build_narrative(data, audience)

    if "all" not in requested_sections:
        narrative["sections"] = [
            s for s in narrative["sections"]
            if any(kw in s["title"].lower() for kw in requested_sections)
        ]

    if output_format == "text":
        lines = [f"BOARD PACK — {period}", "=" * 50, ""]
        for section in narrative["sections"]:
            lines.append(f"## {section['title']}")
            if "content" in section:
                lines.append(section["content"])
            elif "metrics" in section:
                for k, v in section["metrics"].items():
                    if isinstance(v, float):
                        lines.append(f"  {k}: {v:,.2f}")
                    else:
                        lines.append(f"  {k}: {v}")
            elif "detail" in section:
                lines.append(json.dumps(section["detail"], indent=2))
            lines.append("")
        result = "\n".join(lines)
    else:
        result = json.dumps(narrative, indent=2)

    print(result)


if __name__ == "__main__":
    main()
