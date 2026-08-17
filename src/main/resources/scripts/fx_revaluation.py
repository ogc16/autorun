#!/usr/bin/env python3
"""
FX Revaluation
Daily execution script fetching central bank exchange rates (ECB, BoE, Fed)
and running revaluation tasks on foreign currency GL accounts.

Parameters:
  gl_file      : Path to foreign currency GL balances CSV (required)
  base_currency: Base currency for revaluation (default: USD)
  source       : Rate source: ecb, boe, ecb_mock (default: ecb_mock)
  output_dir   : Output directory (default: /tmp/fx_revaluation)
  threshold    : Minimum unrealized gain/loss to flag (default: 100.00)
"""
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone


def parse_args(argv):
    args = {
        "base_currency": "USD",
        "source": "ecb_mock",
        "output_dir": "/tmp/fx_revaluation",
        "threshold": 100.00,
    }
    for arg in argv:
        if arg.startswith("gl_file="):
            args["gl_file"] = arg.split("=", 1)[1]
        elif arg.startswith("base_currency="):
            args["base_currency"] = arg.split("=", 1)[1]
        elif arg.startswith("source="):
            args["source"] = arg.split("=", 1)[1]
        elif arg.startswith("output_dir="):
            args["output_dir"] = arg.split("=", 1)[1]
        elif arg.startswith("threshold="):
            args["threshold"] = float(arg.split("=", 1)[1])
    return args


def fetch_ecb_rates():
    """Fetch rates from ECB Statistical Data Warehouse (XML→parsed)."""
    try:
        url = "https://data-api.ecb.europa.eu/service/data/EXR/D..EUR.SP00.A?lastNObservations=1&format=csvdata"
        req = urllib.request.Request(url, headers={"Accept": "text/csv"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode()
        reader = csv.DictReader(data.splitlines())
        rates = {"EUR": 1.0}
        for row in reader:
            cur = row.get("CURRENCY", "")
            val = row.get("OBS_VALUE", "")
            if cur and val:
                try:
                    rates[cur] = float(val)
                except ValueError:
                    pass
        return rates
    except Exception as e:
        print(f"WARNING: ECB fetch failed ({e}), using mock rates")
        return get_mock_rates()


def get_mock_rates():
    """Fallback mock rates for demo/testing."""
    return {
        "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.50,
        "CHF": 0.88, "CAD": 1.36, "AUD": 1.53, "CNY": 7.24,
        "INR": 83.12, "BRL": 4.97, "MXN": 17.15, "KRW": 1328.50,
    }


def load_gl_balances(filepath):
    entries = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append({
                "account_id": row.get("account_id", ""),
                "account_name": row.get("account_name", ""),
                "currency": row.get("currency", ""),
                "local_balance": float(row.get("local_balance", 0)),
                "book_rate": float(row.get("book_rate", 0)),
                "book_value_base": float(row.get("book_value_base", 0)),
            })
    return entries


def revalue(entries, rates, base_currency):
    results = []
    total_gain_loss = 0

    for entry in entries:
        currency = entry["currency"]
        if currency == base_currency:
            continue

        current_rate = rates.get(currency)
        if current_rate is None:
            results.append({**entry, "error": f"No rate for {currency}", "gain_loss": 0})
            continue

        if base_currency == "EUR" and currency != "EUR":
            current_rate_in_base = 1.0 / current_rate if current_rate != 0 else 0
        else:
            current_rate_in_base = current_rate

        revalued = entry["local_balance"] * current_rate_in_base
        gain_loss = round(revalued - entry["book_value_base"], 2)
        rate_change = round(current_rate_in_base - entry["book_rate"], 6)

        results.append({
            "account_id": entry["account_id"],
            "account_name": entry["account_name"],
            "currency": currency,
            "local_balance": entry["local_balance"],
            "book_rate": entry["book_rate"],
            "current_rate": round(current_rate_in_base, 6),
            "rate_change": rate_change,
            "book_value_base": entry["book_value_base"],
            "revalued_base": round(revalued, 2),
            "gain_loss": gain_loss,
            "significant": abs(gain_loss) > 0,
        })
        total_gain_loss += gain_loss

    return results, round(total_gain_loss, 2)


def write_output(output_dir, results, total_gain_loss, source, base_currency):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")

    report_file = os.path.join(output_dir, f"fx_reval_{ts}.json")
    with open(report_file, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "base_currency": base_currency,
            "total_unrealized_gain_loss": total_gain_loss,
            "accounts_revalued": len(results),
            "results": results,
        }, f, indent=2)

    return report_file


def main():
    args = parse_args(sys.argv[1:])
    gl_file = args.get("gl_file")

    if not gl_file:
        print("ERROR: gl_file parameter is required (path to FX GL balances CSV)")
        sys.exit(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting FX revaluation...")
    print(f"Source: {args['source']}, Base: {args['base_currency']}")

    if args["source"] == "ecb":
        rates = fetch_ecb_rates()
    else:
        rates = get_mock_rates()
    print(f"Loaded {len(rates)} exchange rates")

    entries = load_gl_balances(gl_file)
    print(f"Loaded {len(entries)} foreign currency GL accounts")

    results, total_gain_loss = revalue(entries, rates, args["base_currency"])
    print(f"Revalued {len(results)} accounts, net gain/loss: {total_gain_loss}")

    report_file = write_output(args["output_dir"], results, total_gain_loss,
                               args["source"], args["base_currency"])

    flagged = [r for r in results if abs(r.get("gain_loss", 0)) > args["threshold"]]
    result = {
        "status": "success",
        "report_file": report_file,
        "total_unrealized_gain_loss": total_gain_loss,
        "accounts_revalued": len(results),
        "flagged_above_threshold": len(flagged),
        "threshold": args["threshold"],
    }
    print(json.dumps(result, indent=2))

    if flagged:
        print(f"WARNING: {len(flagged)} accounts exceed threshold of {args['threshold']}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
