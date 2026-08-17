#!/usr/bin/env python3
"""
Rolling Forecast Engine
Projects revenue and expenses forward using configurable methods
(linear, exponential smoothing, or moving average).

Parameters:
  horizon      : Months to forecast ahead (default: 12)
  method       : linear | exponential_smoothing | moving_avg (default: linear)
  smooth_alpha : Smoothing factor 0-1 for exponential method (default: 0.3)
  base_file    : Path to historical data JSON (optional, uses demo data)
"""
import json
import math
import os
import sys
from datetime import datetime


def parse_args(argv):
    now = datetime.now()
    args = {
        "horizon": 12,
        "method": "linear",
        "smooth_alpha": 0.3,
        "base_file": "",
    }
    for arg in argv:
        if arg.startswith("horizon="):
            args["horizon"] = int(arg.split("=", 1)[1])
        elif arg.startswith("method="):
            args["method"] = arg.split("=", 1)[1]
        elif arg.startswith("smooth_alpha="):
            args["smooth_alpha"] = float(arg.split("=", 1)[1])
        elif arg.startswith("base_file="):
            args["base_file"] = arg.split("=", 1)[1]
    return args


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_history():
    base_rev = 420000
    base_cogs = 126000
    base_opex = 210000
    months = []
    for i in range(12):
        dt = datetime.now().replace(day=1)
        dt = dt.replace(month=dt.month - i if dt.month - i > 0 else dt.month - i + 12)
        if dt.month - i <= 0:
            dt = dt.replace(year=dt.year - 1)
        rev = base_rev * (1 + 0.04 * i + (-0.02 if i % 3 == 0 else 0))
        cogs = base_cogs * (1 + 0.03 * i)
        opex = base_opex * (1 + 0.02 * i)
        months.append({
            "month": dt.strftime("%Y-%m"),
            "revenue": round(rev, 2),
            "cogs": round(cogs, 2),
            "opex": round(opex, 2),
            "net_income": round(rev - cogs - opex, 2),
        })
    months.reverse()
    return months


def forecast_linear(values, horizon, alpha=None):
    n = len(values)
    if n < 2:
        last = values[-1] if values else 0
        return [round(last, 2)] * horizon
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den else 0
    intercept = y_mean - slope * x_mean
    return [round(intercept + slope * (n + i), 2) for i in range(horizon)]


def forecast_exp_smoothing(values, horizon, alpha=0.3):
    if not values:
        return [0.0] * horizon
    s = [values[0]]
    for i in range(1, len(values)):
        s.append(alpha * values[i] + (1 - alpha) * s[-1])
    last = s[-1]
    trend = (s[-1] - s[-max(3, len(s))]) / max(3, len(s) - 1) if len(s) > 1 else 0
    return [round(last + trend * (i + 1), 2) for i in range(horizon)]


def forecast_moving_avg(values, horizon, window=3):
    if len(values) < window:
        avg = sum(values) / len(values) if values else 0
        return [round(avg, 2)] * horizon
    recent = values[-window:]
    avg = sum(recent) / len(recent)
    trend = (values[-1] - values[-window]) / window if window else 0
    return [round(avg + trend * (i + 1), 2) for i in range(horizon)]


def main():
    args = parse_args(sys.argv[1:])
    horizon = args["horizon"]
    method = args["method"]
    alpha = args["smooth_alpha"]

    data = load_json(args["base_file"]) if args["base_file"] else None
    if not data or "history" not in data:
        data = {"history": generate_history()}

    history = data["history"]
    revenues = [m["revenue"] for m in history]
    cogs = [m["cogs"] for m in history]
    opex = [m["opex"] for m in history]

    if method == "exponential_smoothing":
        rev_fc = forecast_exp_smoothing(revenues, horizon, alpha)
        cogs_fc = forecast_exp_smoothing(cogs, horizon, alpha)
        opex_fc = forecast_exp_smoothing(opex, horizon, alpha)
    elif method == "moving_avg":
        rev_fc = forecast_moving_avg(revenues, horizon)
        cogs_fc = forecast_moving_avg(cogs, horizon)
        opex_fc = forecast_moving_avg(opex, horizon)
    else:
        rev_fc = forecast_linear(revenues, horizon)
        cogs_fc = forecast_linear(cogs, horizon)
        opex_fc = forecast_linear(opex, horizon)

    last_month = history[-1]["month"] if history else datetime.now().strftime("%Y-%m")
    forecasts = []
    y, m = int(last_month[:4]), int(last_month[5:7])
    for i in range(horizon):
        m += 1
        if m > 12:
            m = 1
            y += 1
        ni = rev_fc[i] - cogs_fc[i] - opex_fc[i]
        forecasts.append({
            "month": f"{y}-{m:02d}",
            "revenue": rev_fc[i],
            "cogs": cogs_fc[i],
            "opex": opex_fc[i],
            "net_income": round(ni, 2),
            "gross_margin_pct": round((rev_fc[i] - cogs_fc[i]) / rev_fc[i] * 100, 1) if rev_fc[i] else 0,
        })

    avg_rev_growth = 0
    if len(revenues) >= 2:
        avg_rev_growth = (revenues[-1] - revenues[0]) / len(revenues)

    result = {
        "method": method,
        "horizon_months": horizon,
        "smoothing_alpha": alpha if method == "exponential_smoothing" else None,
        "history_months": len(history),
        "avg_monthly_revenue_growth": round(avg_rev_growth, 2),
        "forecast_summary": {
            "total_forecast_revenue": round(sum(rev_fc), 2),
            "total_forecast_cogs": round(sum(cogs_fc), 2),
            "total_forecast_opex": round(sum(opex_fc), 2),
            "total_forecast_net_income": round(sum(rev_fc) - sum(cogs_fc) - sum(opex_fc), 2),
            "avg_monthly_revenue": round(sum(rev_fc) / horizon, 2),
        },
        "forecasts": forecasts,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
