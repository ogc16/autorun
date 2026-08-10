#!/usr/bin/env bash
# AutoRun sample: provision a new Linux user (Linux). Requires root.
# Usage: add_user.sh <username>
set -euo pipefail

USERNAME="${1:?Usage: add_user.sh <username>}"

if id "$USERNAME" &>/dev/null; then
  echo "[add_user] User '$USERNAME' already exists."
  exit 0
fi

useradd -m -s /bin/bash "$USERNAME"
echo "[add_user] Created user '$USERNAME' with home directory /home/${USERNAME}."
echo "[add_user] Done."
