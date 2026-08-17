#!/usr/bin/env python3
"""
Ansible Integration — Playbook Runner
Runs Ansible playbooks, inventories, and ad-hoc commands from AutoRun.
Agentless automation for server provisioning, patching, and configuration.

Parameters:
  action     : run, list, inventory, ping, check (default: run)
  playbook   : Path to the playbook YAML (required for action=run)
  inventory  : Path to inventory file or comma-separated host list (required)
  limit      : Limit playbook to specific hosts (default: all)
  tags       : Run only specific tags (default: all)
  extra_vars : JSON string of extra variables to pass (default: {})
  become     : Use sudo/become privilege escalation (default: true)
  check_mode : Dry-run / check mode (default: false)
  verbosity  : Verbosity level 0-4 (default: 0)
  ssh_key    : Path to SSH private key (default: none)
  vault_pass : Vault password file path (default: none)
  log_dir    : Directory for playbook logs (default: /var/log/autorun-patches)
"""
import json
import os
import subprocess
import sys
from datetime import datetime


def find_ansible():
    for cmd in ["ansible-playbook", "/usr/bin/ansible-playbook",
                "/usr/local/bin/ansible-playbook",
                os.path.expanduser("~/.local/bin/ansible-playbook")]:
        r = subprocess.run(["which", cmd] if os.name != "nt" else ["where", cmd],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().splitlines()[0]
    return "ansible-playbook"


def find_ansible_cmd():
    for cmd in ["ansible", "/usr/bin/ansible", "/usr/local/bin/ansible"]:
        r = subprocess.run(["which", cmd] if os.name != "nt" else ["where", cmd],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().splitlines()[0]
    return "ansible"


def run_playbook(ansible_playbook, playbook, inventory, limit, tags,
                 extra_vars, become, check_mode, verbosity, ssh_key,
                 vault_pass, log_file):
    cmd = [ansible_playbook, playbook, "-i", inventory]

    if become:
        cmd.append("--become")
    if check_mode:
        cmd.append("--check")
    if limit:
        cmd.extend(["--limit", limit])
    if tags:
        cmd.extend(["--tags", tags])
    if extra_vars:
        cmd.extend(["--extra-vars", extra_vars])
    if verbosity > 0:
        cmd.append("-" + "v" * min(verbosity, 4))
    if ssh_key:
        cmd.extend(["--private-key", ssh_key])
    if vault_pass:
        cmd.extend(["--vault-password-file", vault_pass])
    cmd.extend(["-e", f"run_timestamp={datetime.utcnow().isoformat()}Z"])

    log(f"Running: {' '.join(cmd)}", log_file)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    log(f"Exit code: {result.returncode}", log_file)
    if result.stdout:
        log(result.stdout[-3000:], log_file)
    if result.stderr:
        log("STDERR: " + result.stderr[-2000:], log_file)

    return {"exit_code": result.returncode, "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-2000:]}


def run_ping(ansible_cmd, inventory, ssh_key, log_file):
    cmd = [ansible_cmd, "all", "-m", "ping", "-i", inventory]
    if ssh_key:
        cmd.extend(["--private-key", ssh_key])
    log(f"Pinging hosts: {' '.join(cmd)}", log_file)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    log(f"Exit code: {result.returncode}", log_file)
    if result.stdout:
        log(result.stdout[-2000:], log_file)
    return {"exit_code": result.returncode, "output": result.stdout[-2000:]}


def run_inventory_check(inventory, log_file):
    cmd = ["ansible-inventory", "--list", "-i", inventory]
    log(f"Listing inventory: {' '.join(cmd)}", log_file)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        try:
            inv_data = json.loads(result.stdout)
            groups = [k for k in inv_data if not k.startswith("_")]
            hosts = inv_data.get("all", {}).get("children", {})
            total = sum(len(inv_data.get(g, {}).get("hosts", [])) for g in groups)
            log(f"Groups: {groups}, Total hosts: {total}", log_file)
            return {"exit_code": 0, "groups": groups, "total_hosts": total,
                    "inventory": inv_data}
        except json.JSONDecodeError:
            return {"exit_code": 0, "raw": result.stdout[-2000:]}
    return {"exit_code": result.returncode, "error": result.stderr[-1000:]}


def log(msg, log_file):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if log_file:
        with open(log_file, "a") as f:
            f.write(line + "\n")


def main():
    action = "run"
    playbook = ""
    inventory = ""
    limit = ""
    tags = ""
    extra_vars = "{}"
    become = True
    check_mode = False
    verbosity = 0
    ssh_key = ""
    vault_pass = ""
    log_dir = "/var/log/autorun-patches"

    for arg in sys.argv[1:]:
        if arg.startswith("action="):
            action = arg.split("=", 1)[1]
        elif arg.startswith("playbook="):
            playbook = arg.split("=", 1)[1]
        elif arg.startswith("inventory="):
            inventory = arg.split("=", 1)[1]
        elif arg.startswith("limit="):
            limit = arg.split("=", 1)[1]
        elif arg.startswith("tags="):
            tags = arg.split("=", 1)[1]
        elif arg.startswith("extra_vars="):
            extra_vars = arg.split("=", 1)[1]
        elif arg.startswith("become="):
            become = arg.split("=", 1)[1].lower() == "true"
        elif arg.startswith("check_mode="):
            check_mode = arg.split("=", 1)[1].lower() == "true"
        elif arg.startswith("verbosity="):
            verbosity = int(arg.split("=", 1)[1])
        elif arg.startswith("ssh_key="):
            ssh_key = arg.split("=", 1)[1]
        elif arg.startswith("vault_pass="):
            vault_pass = arg.split("=", 1)[1]
        elif arg.startswith("log_dir="):
            log_dir = arg.split("=", 1)[1]

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"ansible-{datetime.now().strftime('%Y%m%d')}.log")

    ansible_playbook = find_ansible()
    ansible_cmd = find_ansible_cmd()

    output = {"action": action, "timestamp": datetime.utcnow().isoformat() + "Z"}

    if action == "run":
        if not playbook or not inventory:
            print(json.dumps({"error": "playbook and inventory are required for action=run"}))
            sys.exit(1)
        output["result"] = run_playbook(ansible_playbook, playbook, inventory,
                                         limit, tags, extra_vars, become, check_mode,
                                         verbosity, ssh_key, vault_pass, log_file)
    elif action == "ping":
        if not inventory:
            print(json.dumps({"error": "inventory is required for action=ping"}))
            sys.exit(1)
        output["result"] = run_ping(ansible_cmd, inventory, ssh_key, log_file)
    elif action == "inventory":
        if not inventory:
            print(json.dumps({"error": "inventory is required for action=inventory"}))
            sys.exit(1)
        output["result"] = run_inventory_check(inventory, log_file)
    elif action == "check":
        if not playbook or not inventory:
            print(json.dumps({"error": "playbook and inventory are required for action=check"}))
            sys.exit(1)
        output["result"] = run_playbook(ansible_playbook, playbook, inventory,
                                         limit, tags, extra_vars, become, True,
                                         verbosity, ssh_key, vault_pass, log_file)
    else:
        print(json.dumps({"error": f"Unknown action: {action}"}))
        sys.exit(1)

    output["ansible_version"] = ansible_playbook
    print(json.dumps(output, indent=2))
    sys.exit(output.get("result", {}).get("exit_code", 0))


if __name__ == "__main__":
    main()
