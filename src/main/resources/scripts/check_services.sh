#!/usr/bin/env bash
# Check systemd service status and optionally restart failed ones.
# Usage: check_services.sh [service1] [service2] ...
# If no arguments, checks common services.

set -euo pipefail

RESTART="${RESTART_FAILED:-false}"

if [ $# -eq 0 ]; then
    SERVICES=(nginx mysql postgresql docker ssh cron)
else
    SERVICES=("$@")
fi

FAILED=0
CHECKED=0

echo "========================================"
echo "SERVICE HEALTH CHECK"
echo "========================================"

for svc in "${SERVICES[@]}"; do
    if ! systemctl is-enabled "$svc" &>/dev/null; then
        echo "  [SKIP]  $svc (not installed)"
        continue
    fi
    CHECKED=$((CHECKED + 1))
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || true)
    if [ "$STATUS" = "active" ]; then
        echo "  [OK]    $svc"
    else
        echo "  [FAIL]  $svc  (status: $STATUS)"
        FAILED=$((FAILED + 1))
        if [ "$RESTART" = "true" ]; then
            echo "          Restarting $svc ..."
            if systemctl restart "$svc" 2>/dev/null; then
                echo "          Restarted successfully."
            else
                echo "          Restart FAILED."
            fi
        fi
    fi
done

echo ""
echo "Checked: $CHECKED | Failed: $FAILED"

if [ $FAILED -gt 0 ]; then
    echo "ACTION REQUIRED: $FAILED service(s) are not running."
    exit 1
else
    echo "All services healthy."
    exit 0
fi
