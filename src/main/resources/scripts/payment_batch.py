#!/usr/bin/env python3
"""
Batch Payment File Generation
Generates ISO 20022 / ISO XML payment files from ERP payment queues
and prepares them for SFTP upload to banking portals.

Parameters:
  payments_file : Path to payments queue CSV (required)
  format        : Output format: iso20022, csv, json (default: iso20022)
  company_id    : Company identifier / LEI (required)
  output_dir    : Output directory (default: /tmp/payments)
  sftp_host     : SFTP host for upload (optional, demo only)
"""
import csv
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone


def parse_args(argv):
    args = {
        "format": "iso20022",
        "output_dir": "/tmp/payments",
        "sftp_host": "",
    }
    for arg in argv:
        if arg.startswith("payments_file="):
            args["payments_file"] = arg.split("=", 1)[1]
        elif arg.startswith("format="):
            args["format"] = arg.split("=", 1)[1]
        elif arg.startswith("company_id="):
            args["company_id"] = arg.split("=", 1)[1]
        elif arg.startswith("output_dir="):
            args["output_dir"] = arg.split("=", 1)[1]
        elif arg.startswith("sftp_host="):
            args["sftp_host"] = arg.split("=", 1)[1]
    return args


def load_payments(filepath):
    payments = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            payments.append({
                "payment_id": row.get("payment_id", str(uuid.uuid4())[:8]),
                "payee_name": row.get("payee_name", ""),
                "payee_iban": row.get("payee_iban", ""),
                "payee_bic": row.get("payee_bic", ""),
                "amount": float(row.get("amount", 0)),
                "currency": row.get("currency", "EUR"),
                "reference": row.get("reference", ""),
                "description": row.get("description", ""),
                "payment_date": row.get("payment_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                "payment_type": row.get("payment_type", "SEPA_CREDIT"),
            })
    return payments


def generate_iso20022(payments, company_id, msg_id):
    """Generate ISO 20022 pain.001 XML payment initiation."""
    now = datetime.now(timezone.utc).isoformat()
    total = sum(p["amount"] for p in payments)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">',
        '  <CstmrCdtTrfInfntn>',
        f'    <MsgId>{msg_id}</MsgId>',
        f'    <CreDtTm>{now}</CreDtTm>',
        '    <NbOfTxs>' + str(len(payments)) + '</NbOfTxs>',
        f'    <CtrlSum>{total:.2f}</CtrlSum>',
        '    <InitgPty><Nm>AutoRun ERP</Nm></InitgPty>',
        '    <PmtInf>',
        f'      <PmtInfId>{msg_id}-PMT</PmtInfId>',
        '      <PmtMtd>TRF</PmtMtd>',
        '      <BtchBookg>true</BtchBookg>',
        f'      <ReqdExctnDt><Dt>{payments[0]["payment_date"]}</Dt></ReqdExctnDt>',
        '      <Dbtr><Nm>' + company_id + '</Nm></Dbtr>',
        '    </PmtInf>',
    ]

    for p in payments:
        lines.extend([
            '    <CdtTrfTxInf>',
            f'      <PmtId><EndToEndId>{p["payment_id"]}</EndToEndId></PmtId>',
            f'      <Amt><InstdCcy="{p["currency"]}">{p["amount"]:.2f}</InstdCcy></Amt>',
            f'      <CdtrAgt><FinInstnId><BICFI>{p["payee_bic"]}</BICFI></FinInstnId></CdtrAgt>',
            f'      <Cdtr><Nm>{p["payee_name"]}</Nm></Cdtr>',
            f'      <CdtrAcct><Id><IBAN>{p["payee_iban"]}</IBAN></Id></CdtrAcct>',
            f'      <RmtInf><Ustrd>{p["reference"]} {p["description"]}</Ustrd></RmtInf>',
            '    </CdtTrfTxInf>',
        ])

    lines.extend(['  </CstmrCdtTrfInfntn>', '</Document>'])
    return "\n".join(lines)


def write_output(output_dir, payments, company_id, fmt):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    msg_id = f"AUTORUN-{company_id}-{ts}"
    total = sum(p["amount"] for p in payments)

    if fmt == "iso20022":
        xml_content = generate_iso20022(payments, company_id, msg_id)
        filename = f"pain001_{ts}.xml"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as f:
            f.write(xml_content)
    elif fmt == "csv":
        filename = f"payments_{ts}.csv"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(payments[0].keys()))
            writer.writeheader()
            writer.writerows(payments)
    else:
        filename = f"payments_{ts}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as f:
            json.dump(payments, f, indent=2)

    checksum = hashlib.sha256(open(filepath, "rb").read()).hexdigest()

    manifest = {
        "message_id": msg_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "format": fmt,
        "file": filename,
        "checksum_sha256": checksum,
        "payment_count": len(payments),
        "total_amount": round(total, 2),
        "currency": payments[0]["currency"] if payments else "EUR",
        "sftp_uploaded": False,
    }
    manifest_file = os.path.join(output_dir, f"manifest_{ts}.json")
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    return filepath, manifest_file, manifest


def main():
    args = parse_args(sys.argv[1:])
    payments_file = args.get("payments_file")
    company_id = args.get("company_id")

    if not payments_file:
        print("ERROR: payments_file parameter is required (path to payments CSV)")
        sys.exit(1)
    if not company_id:
        print("ERROR: company_id parameter is required (company LEI or ID)")
        sys.exit(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Generating payment batch file...")
    print(f"Format: {args['format']}, Company: {company_id}")

    payments = load_payments(payments_file)
    print(f"Loaded {len(payments)} payment instructions")

    total = sum(p["amount"] for p in payments)
    print(f"Total payment amount: {total:,.2f}")

    filepath, manifest_file, manifest = write_output(
        args["output_dir"], payments, company_id, args["format"]
    )

    result = {
        "status": "success",
        "message_id": manifest["message_id"],
        "payment_file": filepath,
        "manifest": manifest_file,
        "payment_count": len(payments),
        "total_amount": manifest["total_amount"],
        "checksum": manifest["checksum_sha256"][:16] + "...",
    }
    if args["sftp_host"]:
        result["sftp_host"] = args["sftp_host"]
        result["note"] = "SFTP upload simulated — connect to real host in production"

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
