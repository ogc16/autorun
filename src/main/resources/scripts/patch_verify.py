#!/usr/bin/env python3
"""
Patch Verification Script
Cross-platform script to check installed versions of OS packages,
pip packages, npm packages, Java, Docker, and system components.
Outputs a structured report for compliance and audit.

Parameters:
  components : Comma-separated list to check (default: all)
               Options: os, pip, npm, java, docker, system
  output     : Output format: json or table (default: json)
"""
import json
import os
import platform
import subprocess
import sys
from datetime import datetime


def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, -1


def get_os_info():
    info = {
        "component": "os",
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "kernel": None,
        "packages": [],
        "error": None
    }

    if platform.system() == "Linux":
        # Get distro info
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        info["distro"] = line.split("=", 1)[1].strip().strip('"')
                        break

        out, rc = run_cmd(["uname", "-r"])
        info["kernel"] = out if rc == 0 else None

        # Count installed packages
        for pm, cmd in [
            ("apt", ["dpkg", "--get-selections"]),
            ("yum", ["rpm", "-qa"]),
            ("dnf", ["rpm", "-qa"]),
        ]:
            out, rc = run_cmd(cmd)
            if rc == 0 and out:
                count = len([l for l in out.splitlines() if l.strip()])
                info["packages"].append({"manager": pm, "count": count})
                break

    elif platform.system() == "Windows":
        out, rc = run_cmd(["powershell", "-NoProfile", "-Command",
                           "(Get-CimInstance Win32_OperatingSystem).Caption"])
        info["distro"] = out if rc == 0 else "Windows"

        out, rc = run_cmd(["powershell", "-NoProfile", "-Command",
                           "(Get-CimInstance Win32_OperatingSystem).Version"])
        info["kernel"] = out if rc == 0 else None

        # Count installed programs
        out, rc = run_cmd(["powershell", "-NoProfile", "-Command",
                           "(Get-ItemProperty 'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*').Count"])
        if rc == 0 and out:
            info["packages"].append({"manager": "registry", "count": int(out)})

    return info


def get_pip_info():
    info = {"component": "pip", "packages": [], "error": None}

    out, rc = run_cmd([sys.executable, "-m", "pip", "list", "--format=json"])
    if rc != 0:
        info["error"] = "pip not available"
        return info

    try:
        packages = json.loads(out)
        for pkg in packages:
            info["packages"].append({
                "name": pkg["name"],
                "version": pkg["version"]
            })
    except json.JSONDecodeError:
        info["error"] = "Failed to parse pip output"

    return info


def get_npm_info():
    info = {"component": "npm", "packages": [], "error": None}

    out, rc = run_cmd(["npm", "list", "-g", "--depth=0", "--json"])
    if rc != 0:
        info["error"] = "npm not available"
        return info

    try:
        data = json.loads(out)
        deps = data.get("dependencies", {})
        for name, details in deps.items():
            info["packages"].append({
                "name": name,
                "version": details.get("version", "unknown")
            })
    except json.JSONDecodeError:
        info["error"] = "Failed to parse npm output"

    return info


def get_java_info():
    info = {"component": "java", "version": None, "vendor": None, "error": None}

    out, rc = run_cmd(["java", "-version"], timeout=10)
    if rc != 0:
        info["error"] = "java not found"
        return info

    lines = out.splitlines()
    if lines:
        info["version"] = lines[0].strip()
        for line in lines:
            if "openjdk" in line.lower():
                info["vendor"] = "OpenJDK"
            elif "oracle" in line.lower():
                info["vendor"] = "Oracle JDK"

    # JAVA_HOME
    info["java_home"] = os.environ.get("JAVA_HOME", "not set")

    return info


def get_docker_info():
    info = {"component": "docker", "version": None, "containers": [], "images": [], "error": None}

    out, rc = run_cmd(["docker", "--version"])
    if rc != 0:
        info["error"] = "docker not found"
        return info

    info["version"] = out

    # Running containers
    out, rc = run_cmd(["docker", "ps", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}"])
    if rc == 0 and out:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                info["containers"].append({
                    "name": parts[0],
                    "image": parts[1],
                    "status": parts[2]
                })

    return info


def get_system_info():
    info = {"component": "system", "cpu_count": os.cpu_count(),
            "python_version": platform.python_version(),
            "disk_usage": [], "error": None}

    # Disk usage (Linux)
    if platform.system() == "Linux":
        out, rc = run_cmd(["df", "-h", "--output=source,size,used,avail,pcent,target"])
        if rc == 0 and out:
            for line in out.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 6:
                    info["disk_usage"].append({
                        "device": parts[0],
                        "size": parts[1],
                        "used": parts[2],
                        "avail": parts[3],
                        "use_percent": parts[4],
                        "mount": parts[5]
                    })

    elif platform.system() == "Windows":
        out, rc = run_cmd(["powershell", "-NoProfile", "-Command",
                           "Get-PSDrive -PSProvider FileSystem | "
                           "Select-Object Name,@{N='SizeGB';E={[math]::Round($_.Used/1GB,1)}},"
                           "@{N='FreeGB';E={[math]::Round($_.Free/1GB,1)}} | "
                           "ConvertTo-Json"])
        if rc == 0 and out:
            try:
                drives = json.loads(out)
                if isinstance(drives, dict):
                    drives = [drives]
                for d in drives:
                    info["disk_usage"].append({
                        "device": d.get("Name", "?"),
                        "used_gb": d.get("SizeGB", 0),
                        "free_gb": d.get("FreeGB", 0)
                    })
            except json.JSONDecodeError:
                pass

    return info


def main():
    components_raw = "all"
    output_format = "json"

    for arg in sys.argv[1:]:
        if arg.startswith("components="):
            components_raw = arg.split("=", 1)[1]
        elif arg.startswith("output="):
            output_format = arg.split("=", 1)[1]

    CHECKERS = {
        "os": get_os_info,
        "pip": get_pip_info,
        "npm": get_npm_info,
        "java": get_java_info,
        "docker": get_docker_info,
        "system": get_system_info,
    }

    if components_raw == "all":
        components = list(CHECKERS.keys())
    else:
        components = [c.strip() for c in components_raw.split(",")]

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "hostname": platform.node(),
        "checks": []
    }

    for comp in components:
        if comp in CHECKERS:
            report["checks"].append(CHECKERS[comp]())

    if output_format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(f"Patch Verification Report — {report['timestamp']}")
        print(f"Host: {report['hostname']}")
        print("=" * 60)
        for check in report["checks"]:
            comp = check.get("component", "unknown")
            print(f"\n[{comp.upper()}]")
            if "error" in check and check["error"]:
                print(f"  Error: {check['error']}")
            if "version" in check and check["version"]:
                print(f"  Version: {check['version']}")
            if "distro" in check:
                print(f"  Distro: {check['distro']}")
            if "packages" in check:
                pkgs = check["packages"]
                if isinstance(pkgs, list) and pkgs and isinstance(pkgs[0], dict) and "name" in pkgs[0]:
                    print(f"  Packages: {len(pkgs)} installed")
                elif isinstance(pkgs, list):
                    for p in pkgs:
                        print(f"  Manager: {p.get('manager', '?')} — {p.get('count', '?')} packages")
            if "containers" in check:
                print(f"  Containers: {len(check['containers'])} running")
            if "disk_usage" in check:
                for d in check["disk_usage"]:
                    print(f"  Disk: {d.get('device', '?')} — used {d.get('used', d.get('used_gb', '?'))} / {d.get('size', '?')}")

    sys.exit(0)


if __name__ == "__main__":
    main()
