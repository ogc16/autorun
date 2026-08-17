#!/usr/bin/env python3
"""
Datto RMM Integration — Unified RMM Operations
Connects to Datto Ratto RMM API for remote monitoring, patch management,
scripting, and device management across multiple client sites.

Parameters:
  action     : list_devices, list_sites, get_device, run_script,
               list_patches, install_patch, get_alerts, get_audit_log,
               list_scripts, get_device_snapshot (required)
  api_url    : Datto RMM API base URL (default: https://centra Westbrook API endpoint — set env: DATTO_API_URL)
  api_key    : Datto RMM API key (or env: DATTO_API_KEY)
  api_secret : Datto RMM API secret (or env: DATTO_API_SECRET)
  site_uid   : Filter by site UID (optional)
  device_uid : Device UID (for device-specific actions)
  script_uid : Script UID (for run_script)
  patch_uid  : Patch UID (for install_patch)
  alert_id   : Alert ID (for alert actions)
  query      : Search query (for device search)
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime


DEFAULT_API_URL = "https://api.datto.com/v1"


def get_auth_header(api_key, api_secret):
    credentials = f"{api_key}:{api_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def api_request(api_url, api_key, api_secret, method, path, params=None, body=None):
    url = f"{api_url}{path}"
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v})
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": get_auth_header(api_key, api_secret),
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else {"status": "ok"}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        try:
            return json.loads(err_body)
        except json.JSONDecodeError:
            return {"error": f"HTTP {e.code}: {err_body[:500]}"}


def list_devices(api_url, api_key, api_secret, site_uid, query, log_file):
    log(f"Listing devices (site={site_uid}, query={query})", log_file)
    params = {}
    if site_uid:
        params["siteUid"] = site_uid
    if query:
        params["query"] = query
    result = api_request(api_url, api_key, api_secret, "GET", "/rmm/device", params)
    if isinstance(result, dict) and "devices" in result:
        devices = result["devices"]
        log(f"  Found {len(devices)} device(s)", log_file)
        for d in devices[:5]:
            log(f"  - {d.get('hostname', '?')} ({d.get('platform', '?')})", log_file)
    return result


def list_sites(api_url, api_key, api_secret, log_file):
    log("Listing sites", log_file)
    result = api_request(api_url, api_key, api_secret, "GET", "/rmm/site")
    if isinstance(result, dict) and "sites" in result:
        sites = result["sites"]
        log(f"  Found {len(sites)} site(s)", log_file)
        for s in sites[:5]:
            log(f"  - {s.get('name', '?')} (UID: {s.get('uid', '?')})", log_file)
    return result


def get_device(api_url, api_key, api_secret, device_uid, log_file):
    log(f"Getting device: {device_uid}", log_file)
    return api_request(api_url, api_key, api_secret, "GET",
                       f"/rmm/device/{device_uid}")


def run_script(api_url, api_key, api_secret, device_uid, script_uid, log_file):
    log(f"Running script {script_uid} on device {device_uid}", log_file)
    body = {"deviceUid": device_uid, "scriptUid": script_uid}
    return api_request(api_url, api_key, api_secret, "POST", "/rmm/script/run", body=body)


def list_patches(api_url, api_key, api_secret, device_uid, log_file):
    log(f"Listing patches for device {device_uid}", log_file)
    result = api_request(api_url, api_key, api_secret, "GET",
                         f"/rmm/device/{device_uid}/patches")
    if isinstance(result, dict) and "patches" in result:
        patches = result["patches"]
        log(f"  Found {len(patches)} patch(es)", log_file)
        for p in patches[:5]:
            log(f"  - {p.get('name', '?')} [{p.get('status', '?')}]", log_file)
    return result


def install_patch(api_url, api_key, api_secret, device_uid, patch_uid, log_file):
    log(f"Installing patch {patch_uid} on device {device_uid}", log_file)
    body = {"deviceUid": device_uid, "patchUid": patch_uid}
    return api_request(api_url, api_key, api_secret, "POST",
                       "/rmm/patch/install", body=body)


def get_alerts(api_url, api_key, api_secret, site_uid, log_file):
    log(f"Listing alerts (site={site_uid})", log_file)
    params = {}
    if site_uid:
        params["siteUid"] = site_uid
    result = api_request(api_url, api_key, api_secret, "GET", "/rmm/alert", params)
    if isinstance(result, dict) and "alerts" in result:
        alerts = result["alerts"]
        log(f"  Found {len(alerts)} alert(s)", log_file)
        for a in alerts[:5]:
            log(f"  - [{a.get('severity', '?')}] {a.get('message', '?')}", log_file)
    return result


def get_audit_log(api_url, api_key, api_secret, site_uid, log_file):
    log("Getting audit log", log_file)
    params = {}
    if site_uid:
        params["siteUid"] = site_uid
    return api_request(api_url, api_key, api_secret, "GET", "/rmm/audit", params)


def list_scripts(api_url, api_key, api_secret, log_file):
    log("Listing available scripts", log_file)
    result = api_request(api_url, api_key, api_secret, "GET", "/rmm/script")
    if isinstance(result, dict) and "scripts" in result:
        scripts = result["scripts"]
        log(f"  Found {len(scripts)} script(s)", log_file)
        for s in scripts[:5]:
            log(f"  - {s.get('name', '?')} (UID: {s.get('uid', '?')})", log_file)
    return result


def log(msg, log_file):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if log_file:
        with open(log_file, "a") as f:
            f.write(line + "\n")


def main():
    action = ""
    api_url = os.environ.get("DATTO_API_URL", DEFAULT_API_URL)
    api_key = os.environ.get("DATTO_API_KEY", "")
    api_secret = os.environ.get("DATTO_API_SECRET", "")
    site_uid = ""
    device_uid = ""
    script_uid = ""
    patch_uid = ""
    alert_id = ""
    query = ""
    log_dir = "/var/log/autorun-patches"

    for arg in sys.argv[1:]:
        if arg.startswith("action="):
            action = arg.split("=", 1)[1]
        elif arg.startswith("api_url="):
            api_url = arg.split("=", 1)[1]
        elif arg.startswith("api_key="):
            api_key = arg.split("=", 1)[1]
        elif arg.startswith("api_secret="):
            api_secret = arg.split("=", 1)[1]
        elif arg.startswith("site_uid="):
            site_uid = arg.split("=", 1)[1]
        elif arg.startswith("device_uid="):
            device_uid = arg.split("=", 1)[1]
        elif arg.startswith("script_uid="):
            script_uid = arg.split("=", 1)[1]
        elif arg.startswith("patch_uid="):
            patch_uid = arg.split("=", 1)[1]
        elif arg.startswith("alert_id="):
            alert_id = arg.split("=", 1)[1]
        elif arg.startswith("query="):
            query = arg.split("=", 1)[1]
        elif arg.startswith("log_dir="):
            log_dir = arg.split("=", 1)[1]

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"datto-rmm-{datetime.now().strftime('%Y%m%d')}.log")

    if not action:
        print(json.dumps({"error": "action parameter is required"}))
        sys.exit(1)

    if not api_key or not api_secret:
        print(json.dumps({"error": "api_key and api_secret required (set DATTO_API_KEY, DATTO_API_SECRET env vars)"}))
        sys.exit(1)

    log(f"Datto RMM — action={action}", log_file)

    output = {"action": action, "timestamp": datetime.utcnow().isoformat() + "Z"}

    handlers = {
        "list_devices": lambda: list_devices(api_url, api_key, api_secret, site_uid, query, log_file),
        "list_sites": lambda: list_sites(api_url, api_key, api_secret, log_file),
        "get_device": lambda: get_device(api_url, api_key, api_secret, device_uid, log_file),
        "run_script": lambda: run_script(api_url, api_key, api_secret, device_uid, script_uid, log_file),
        "list_patches": lambda: list_patches(api_url, api_key, api_secret, device_uid, log_file),
        "install_patch": lambda: install_patch(api_url, api_key, api_secret, device_uid, patch_uid, log_file),
        "get_alerts": lambda: get_alerts(api_url, api_key, api_secret, site_uid, log_file),
        "get_audit_log": lambda: get_audit_log(api_url, api_key, api_secret, site_uid, log_file),
        "list_scripts": lambda: list_scripts(api_url, api_key, api_secret, log_file),
    }

    if action not in handlers:
        print(json.dumps({"error": f"Unknown action: {action}. Available: {list(handlers.keys())}"}))
        sys.exit(1)

    result = handlers[action]()
    output["result"] = result
    print(json.dumps(output, indent=2))
    sys.exit(0 if "error" not in result else 1)


if __name__ == "__main__":
    main()
