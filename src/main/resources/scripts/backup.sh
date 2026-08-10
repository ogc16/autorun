#!/usr/bin/env bash
# AutoRun sample: tar backup of a directory (Linux).
# Usage: backup.sh <src> <dest>
set -euo pipefail

SRC="${1:-/var/www}"
DEST="${2:-./backups}"

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="${DEST}/backup_${STAMP}.tar.gz"

mkdir -p "$DEST"

echo "[backup] Archiving ${SRC} -> ${OUT}"
tar -czf "$OUT" -C "$(dirname "$SRC")" "$(basename "$SRC")"

SIZE=$(du -h "$OUT" | cut -f1)
echo "[backup] Created ${OUT} (${SIZE})"
echo "[backup] Done."
