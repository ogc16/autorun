#!/usr/bin/env python3
"""
System Inventory Script
Discovers servers, endpoints, and applications that need patching.
Collects OS info, installed packages, running services, listening ports,
and network details. Outputs structured JSON for compliance reporting.

Parameters:
  include_ports  : Include listening ports in report (default: true)
  include_services : Include running services (default: true)
  include_packages : Include installed package counts (default: true)
"""
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime


def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, -1


def get_network_info():
    info = {"hostname": platform.node(), "fqdn": None, "ip_addresses": [], "interfaces": []}

    try:
        info["fqdn"] = socket.getfqdn()
    except Exception:
        pass

    # Get IP addresses
    if platform.system() == "Linux":
        out, rc = run_cmd(["hostname", "-I"])
        if rc == 0 and out:
            info["ip_addresses"] = [ip.strip() for ip in out.split() if ip.strip()]

        out, rc = run_cmd(["ip", "-o", "addr", "show", "up"])
        if rc == 0 and out:
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    iface = parts[1]
                    addr = parts[3].split("/")[0] if "/" in parts[3] else parts[3]
                    info["interfaces"].append({"name": iface, "address": addr})

    elif platform.system() == "Windows":
        out, rc = run_cmd(["powershell", "-NoProfile", "-Command",
                           "Get-NetIPAddress -AddressFamily IPv4 | "
                           "Select-Object InterfaceAlias,IPAddress | ConvertTo-Json"])
        if rc == 0 and out:
            try:
                addrs = json.loads(out)
                if isinstance(addrs, dict):
                    addrs = [addrs]
                for a in addrs:
                    info["interfaces"].append({
                        "name": a.get("InterfaceAlias", "?"),
                        "address": a.get("IPAddress", "?")
                    })
                    info["ip_addresses"].append(a.get("IPAddress", ""))
            except json.JSONDecodeError:
                pass

    return info


def get_listening_ports():
    ports = []

    if platform.system() == "Linux":
        out, rc = run_cmd(["ss", "-tlnp"])
        if rc == 0 and out:
            for line in out.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 5:
                    local = parts[3]
                    proc = parts[-1] if "=" in parts[-1] else ""
                    ports.append({"address": local, "process": proc})

    elif platform.system() == "Windows":
        out, rc = run_cmd(["powershell", "-NoProfile", "-Command",
                           "Get-NetTCPConnection -State Listen | "
                           "Select-Object LocalPort,LocalAddress,OwningProcess | "
                           "ConvertTo-Json"])
        if rc == 0 and out:
            try:
                conns = json.loads(out)
                if isinstance(conns, dict):
                    conns = [conns]
                for c in conns:
                    ports.append({
                        "address": f"{c.get('LocalAddress', '?')}:{c.get('LocalPort', '?')}",
                        "process": str(c.get("OwningProcess", "?"))
                    })
            except json.JSONDecodeError:
                pass

    return ports


def get_running_services():
    services = []

    if platform.system() == "Linux":
        out, rc = run_cmd(["systemctl", "list-units", "--type=service", "--state=running", "--no-pager", "--no-legend"])
        if rc == 0 and out:
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 1:
                    name = parts[0].replace(".service", "")
                    status = parts[2] if len(parts) >= 3 else "?"
                    services.append({"name": name, "status": status})

    elif platform.system() == "Windows":
        out, rc = run_cmd(["powershell", "-NoProfile", "-Command",
                           "Get-Service | Where-Object {$_.Status -eq 'Running'} | "
                           "Select-Object Name,DisplayName | ConvertTo-Json"])
        if rc == 0 and out:
            try:
                svcs = json.loads(out)
                if isinstance(svcs, dict):
                    svcs = [svcs]
                for s in svcs:
                    services.append({
                        "name": s.get("Name", "?"),
                        "display_name": s.get("DisplayName", "?")
                    })
            except json.JSONDecodeError:
                pass

    return services


def get_package_counts():
    counts = {}

    if platform.system() == "Linux":
        for pm, cmd in [
            ("apt", ["dpkg", "-l"]),
            ("rpm", ["rpm", "-qa"]),
        ]:
            out, rc = run_cmd(cmd)
            if rc == 0 and out:
                counts[pm] = len([l for l in out.splitlines() if l.strip() and not l.startswith("||")])
                break

        # Check for security updates
        if "apt" in counts:
            out, rc = run_cmd(["apt", "list", "--upgradable"])
            if rc == 0 and out:
                counts["upgradable"] = len([l for l in out.splitlines() if "upgradable" in l])

    elif platform.system() == "Windows":
        out, rc = run_cmd(["powershell", "-NoProfile", "-Command",
                           "(Get-ItemProperty 'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*').Count"])
        if rc == 0 and out:
            counts["registry"] = int(out) if out.isdigit() else 0

    return counts


def main():
    include_ports = True
    include_services = True
    include_packages = True

    for arg in sys.argv[1:]:
        if arg.startswith("include_ports="):
            include_ports = arg.split("=", 1)[1].lower() == "true"
        elif arg.startswith("include_services="):
            include_services = arg.split("=", 1)[1].lower() == "true"
        elif arg.startswith("include_packages="):
            include_packages = arg.split("=", 1)[1].lower() == "true"

    inventory = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "system": {
            "os": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "kernel": platform.release()
        },
        "network": get_network_info()
    }

    if include_packages:
        inventory["packages"] = get_package_counts()

    if include_services:
        inventory["services"] = get_running_services()

    if include_ports:
        inventory["listening_ports"] = get_listening_ports()

    print(json.dumps(inventory, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
