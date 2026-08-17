#!/bin/bash
# ============================================================
# Linux Patch Script
# Runs apt update, upgrade, and autoremove on Debian/Ubuntu,
# or yum update on RHEL/CentOS/Amazon Linux.
#
# Parameters:
#   dry_run       - Only check, do not install (default: false)
#   reboot        - Auto-reboot if required (default: false)
#   security_only - Only install security patches (default: false)
# ============================================================
set -euo pipefail

DRY_RUN=false
REBOOT=false
SECURITY_ONLY=false
LOG_DIR="/var/log/autorun-patches"
LOG_FILE="${LOG_DIR}/linux-patch-$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

for arg in "$@"; do
    case "$arg" in
        dry_run=true)       DRY_RUN=true ;;
        reboot=true)        REBOOT=true ;;
        security_only=true) SECURITY_ONLY=true ;;
    esac
done

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

detect_package_manager() {
    if command -v apt-get &>/dev/null; then
        echo "apt"
    elif command -v yum &>/dev/null; then
        echo "yum"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    else
        echo "unknown"
    fi
}

patch_apt() {
    log "Detected Debian/Ubuntu system (apt)"

    log "Running apt-get update..."
    apt-get update -qq >> "$LOG_FILE" 2>&1

    if [ "$DRY_RUN" = true ]; then
        log "Checking available upgrades (dry run)..."
        apt list --upgradable 2>/dev/null | tee -a "$LOG_FILE"
        UPGRADE_COUNT=$(apt list --upgradable 2>/dev/null | grep -c upgradable || true)
        log "Found $UPGRADE_COUNT package(s) with available upgrades."
        return 0
    fi

    if [ "$SECURITY_ONLY" = true ]; then
        log "Installing security-only patches..."
        apt-get install -y -o Dpkg::Options::="--force-confdef" \
            $(apt-get -s upgrade 2>/dev/null | grep -i "Inst" | grep -i secur | awk '{print $2}' | tr '\n' ' ') \
            >> "$LOG_FILE" 2>&1 || true
    else
        log "Installing all available upgrades..."
        DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
            -o Dpkg::Options::="--force-confdef" \
            >> "$LOG_FILE" 2>&1
    fi

    log "Running autoremove..."
    apt-get autoremove -y >> "$LOG_FILE" 2>&1

    log "Checking if reboot is required..."
    if [ -f /var/run/reboot-required ]; then
        log "REBOOT REQUIRED"
        if [ "$REBOOT" = true ]; then
            log "Rebooting in 60 seconds..."
            shutdown -r +1 "System will reboot in 1 minute for patch installation"
        fi
    else
        log "No reboot required."
    fi
}

patch_yum() {
    local PKG_MGR="yum"
    if command -v dnf &>/dev/null; then
        PKG_MGR="dnf"
    fi
    log "Detected RHEL/CentOS/Amazon Linux system ($PKG_MGR)"

    log "Checking for available updates..."
    if [ "$DRY_RUN" = true ]; then
        $PKG_MGR check-update >> "$LOG_FILE" 2>&1 || true
        log "Dry run complete. No changes made."
        return 0
    fi

    if [ "$SECURITY_ONLY" = true ]; then
        log "Installing security-only patches..."
        $PKG_MGR update --security -y >> "$LOG_FILE" 2>&1
    else
        log "Installing all available updates..."
        $PKG_MGR update -y >> "$LOG_FILE" 2>&1
    fi

    log "Cleaning package cache..."
    $PKG_MGR clean all >> "$LOG_FILE" 2>&1

    if needs-restarting -r &>/dev/null; then
        log "REBOOT REQUIRED"
        if [ "$REBOOT" = true ]; then
            log "Rebooting in 60 seconds..."
            shutdown -r +1 "System will reboot in 1 minute for patch installation"
        fi
    else
        log "No reboot required."
    fi
}

# --- Main ---
log "===== Linux Patch Script Started ====="
log "dry_run=$DRY_RUN reboot=$REBOOT security_only=$SECURITY_ONLY"

PKG_MGR=$(detect_package_manager)
log "Package manager: $PKG_MGR"

case "$PKG_MGR" in
    apt) patch_apt ;;
    yum|dnf) patch_yum ;;
    *)
        log "ERROR: Unsupported package manager. Neither apt nor yum/dnf found."
        exit 1
        ;;
esac

log "===== Linux Patch Script Completed ====="
exit 0
