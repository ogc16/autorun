#!/usr/bin/env bash
# Clean temporary files, package manager caches, and old logs.
# Usage: cleanup_temp.sh [max_age_days]

set -euo pipefail

MAX_AGE="${1:-7}"
FREED=0

echo "========================================"
echo "TEMP & CACHE CLEANUP (>${MAX_AGE} days old)"
echo "========================================"

clean_dir() {
    local dir="$1"
    local label="$2"
    if [ -d "$dir" ]; then
        before=$(du -sk "$dir" 2>/dev/null | awk '{print $1}')
        find "$dir" -mindepth 1 -maxdepth 2 -mtime +${MAX_AGE} -delete 2>/dev/null || true
        after=$(du -sk "$dir" 2>/dev/null | awk '{print $1}')
        freed=$(( (before - after) / 1024 ))
        echo "  [$label]  freed ~${freed} MB from $dir"
        FREED=$((FREED + freed))
    fi
}

clean_dir "/tmp" "TEMP"
clean_dir "/var/tmp" "VAR-TMP"
clean_dir "/var/cache/apt/archives" "APT-CACHE"
clean_dir "${HOME}/.cache/pip" "PIP-CACHE"
clean_dir "${HOME}/.npm/_cacache" "NPM-CACHE"
clean_dir "${HOME}/.gradle/caches" "GRADLE-CACHE"

# Clean old log files
if [ -d "/var/log" ]; then
    find /var/log -name "*.gz" -mtime +${MAX_AGE} -delete 2>/dev/null || true
    find /var/log -name "*.old" -mtime +${MAX_AGE} -delete 2>/dev/null || true
    find /var/log -name "*.[0-9]" -mtime +${MAX_AGE} -delete 2>/dev/null || true
    echo "  [LOGS]   cleaned old rotated logs"
fi

echo ""
echo "Done. Approximate total freed: ~${FREED} MB"
