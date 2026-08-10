#!/usr/bin/env bash
# AutoRun sample: APT patching (Linux). Requires root.
set -euo pipefail

echo "[patch] Updating package lists..."
apt-get update

echo "[patch] Upgrading packages..."
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

echo "[patch] Patching complete."
