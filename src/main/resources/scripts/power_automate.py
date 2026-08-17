#!/usr/bin/env python3
"""
Power Automate Integration — Microsoft 365 Business Task Automation
Connects to Microsoft Graph API to automate M365 tasks: user provisioning,
license management, SharePoint operations, Teams notifications, and Outlook.
Requires Azure AD app registration with appropriate permissions.

Parameters:
  action     : create_user, list_users, disable_user, assign_license,
               send_teams_message, send_email, list_sharepoint_files,
               list_groups, add_to_group (required)
  tenant_id  : Azure AD Tenant ID (or env: AZURE_TENANT_ID)
  client_id  : Azure AD App Client ID (or env: AZURE_CLIENT_ID)
  client_secret : Azure AD App Client Secret (or env: AZURE_CLIENT_SECRET)
  user_email : Target user email (for user actions)
  display_name : User display name (for create_user)
  password   : Initial password (for create_user)
  license_sku : License SKU ID (for assign_license)
  message    : Message text (for send_teams_message/send_email)
  channel_id : Teams channel ID (for send_teams_message)
  group_id   : Group ID (for list_groups/add_to_group)
  site_url   : SharePoint site URL (for list_sharepoint_files)
  folder_path : SharePoint folder path (default: /Shared Documents)
"""
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def get_token(tenant_id, client_id, client_secret):
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        body = json.loads(resp.read())
        return body["access_token"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": f"Token request failed ({e.code}): {body}"}


def graph_request(token, method, path, body=None):
    url = f"{GRAPH_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read()) if resp.read() else {"status": "ok"}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        try:
            return json.loads(err_body)
        except json.JSONDecodeError:
            return {"error": f"HTTP {e.code}: {err_body[:500]}"}


def create_user(token, display_name, user_email, password, log_file):
    log(f"Creating user: {display_name} ({user_email})", log_file)
    body = {
        "accountEnabled": True,
        "displayName": display_name,
        "mailNickname": user_email.split("@")[0],
        "userPrincipalName": user_email,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": password
        }
    }
    return graph_request(token, "POST", "/users", body)


def list_users(token, log_file):
    log("Listing users", log_file)
    return graph_request(token, "GET", "/users?$top=50&$select=displayName,mail,accountEnabled,userPrincipalName")


def disable_user(token, user_id, log_file):
    log(f"Disabling user: {user_id}", log_file)
    return graph_request(token, "PATCH", f"/users/{user_id}", {"accountEnabled": False})


def assign_license(token, user_id, sku_id, log_file):
    log(f"Assigning license {sku_id} to {user_id}", log_file)
    return graph_request(token, "POST", f"/users/{user_id}/assignLicense",
                         {"addLicenses": [{"skuId": sku_id}], "removeLicenses": []})


def send_teams_message(token, channel_id, message, log_file):
    log(f"Sending Teams message to {channel_id}", log_file)
    return graph_request(token, "POST",
                         f"/teams/{channel_id.split('/')[0]}/channels/{channel_id.split('/')[1]}/messages",
                         {"body": {"content": message}})


def send_email(token, user_email, subject, body, log_file):
    log(f"Sending email from {user_email}", log_file)
    mail_body = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": []
        },
        "saveToSentItems": "true"
    }
    return graph_request(token, "POST", f"/users/{user_email}/sendMail", mail_body)


def list_sharepoint_files(token, site_url, folder_path, log_file):
    log(f"Listing SharePoint files: {site_url}/{folder_path}", log_file)
    site = graph_request(token, "GET", f"/sites/{site_url}")
    if "error" in site:
        return site
    site_id = site.get("id", "")
    encoded_path = urllib.parse.quote(folder_path.lstrip("/"))
    return graph_request(token, "GET",
                         f"/sites/{site_id}/drive/root:/{encoded_path}:/children")


def list_groups(token, log_file):
    log("Listing groups", log_file)
    return graph_request(token, "GET", "/groups?$top=50&$select=displayName,id,mailEnabled")


def add_to_group(token, group_id, user_id, log_file):
    log(f"Adding {user_id} to group {group_id}", log_file)
    return graph_request(token, "POST", f"/groups/{group_id}/members/$ref",
                         {"@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"})


def log(msg, log_file):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if log_file:
        with open(log_file, "a") as f:
            f.write(line + "\n")


def main():
    action = ""
    tenant_id = os.environ.get("AZURE_TENANT_ID", "")
    client_id = os.environ.get("AZURE_CLIENT_ID", "")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET", "")
    user_email = ""
    display_name = ""
    password = ""
    license_sku = ""
    message = ""
    channel_id = ""
    group_id = ""
    site_url = ""
    folder_path = "/Shared Documents"
    log_dir = "/var/log/autorun-patches"

    for arg in sys.argv[1:]:
        if arg.startswith("action="):
            action = arg.split("=", 1)[1]
        elif arg.startswith("tenant_id="):
            tenant_id = arg.split("=", 1)[1]
        elif arg.startswith("client_id="):
            client_id = arg.split("=", 1)[1]
        elif arg.startswith("client_secret="):
            client_secret = arg.split("=", 1)[1]
        elif arg.startswith("user_email="):
            user_email = arg.split("=", 1)[1]
        elif arg.startswith("display_name="):
            display_name = arg.split("=", 1)[1]
        elif arg.startswith("password="):
            password = arg.split("=", 1)[1]
        elif arg.startswith("license_sku="):
            license_sku = arg.split("=", 1)[1]
        elif arg.startswith("message="):
            message = arg.split("=", 1)[1]
        elif arg.startswith("channel_id="):
            channel_id = arg.split("=", 1)[1]
        elif arg.startswith("group_id="):
            group_id = arg.split("=", 1)[1]
        elif arg.startswith("site_url="):
            site_url = arg.split("=", 1)[1]
        elif arg.startswith("folder_path="):
            folder_path = arg.split("=", 1)[1]
        elif arg.startswith("log_dir="):
            log_dir = arg.split("=", 1)[1]

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"power-automate-{datetime.now().strftime('%Y%m%d')}.log")

    if not action:
        print(json.dumps({"error": "action parameter is required"}))
        sys.exit(1)

    if not all([tenant_id, client_id, client_secret]):
        print(json.dumps({"error": "tenant_id, client_id, client_secret are required (set env vars AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)"}))
        sys.exit(1)

    log(f"Power Automate — action={action}", log_file)
    token = get_token(tenant_id, client_id, client_secret)
    if isinstance(token, dict) and "error" in token:
        print(json.dumps(token, indent=2))
        sys.exit(1)

    output = {"action": action, "timestamp": datetime.utcnow().isoformat() + "Z"}

    handlers = {
        "create_user": lambda: create_user(token, display_name, user_email, password, log_file),
        "list_users": lambda: list_users(token, log_file),
        "disable_user": lambda: disable_user(token, user_email, log_file),
        "assign_license": lambda: assign_license(token, user_email, license_sku, log_file),
        "send_teams_message": lambda: send_teams_message(token, channel_id, message, log_file),
        "send_email": lambda: send_email(token, user_email, message.split("|")[0] if "|" in message else "AutoRun Notification",
                                          message.split("|")[1] if "|" in message else message, log_file),
        "list_sharepoint_files": lambda: list_sharepoint_files(token, site_url, folder_path, log_file),
        "list_groups": lambda: list_groups(token, log_file),
        "add_to_group": lambda: add_to_group(token, group_id, user_email, log_file),
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
