#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   sync_nqch_to_reporting.sh [--propagate] [SOURCE_HOST SOURCE_DIR REPORTING_HOST REPORTING_DIR]
#
# With no positional args, defaults are used:
#   SOURCE_HOST="nqch-machine"
#   SOURCE_DIR="~/CQT-experiments/data"
#   REPORTING_HOST="cqtreporting.tortuga"
#   REPORTING_DIR="/opt/cqt-reporting/data"
#
# Examples:
#   # Default paths, non-destructive (no overwrite on REPORTING)
#   sync_nqch_to_reporting.sh
#
#   # Default paths, but propagate modified files
#   sync_nqch_to_reporting.sh --propagate
#
#   # Custom paths, non-destructive
#   sync_nqch_to_reporting.sh other-nqch /data/foo other-report /var/bar
#
#   # Custom + propagate
#   sync_nqch_to_reporting.sh --propagate other-nqch /data/foo other-report /var/bar

PROPAGATE_CHANGES=false

if [[ "${1-}" == "--propagate" ]]; then
    PROPAGATE_CHANGES=true
    shift
fi

# Defaults (match your current rsync usage)
DEFAULT_SOURCE_HOST="nqch-machine"
DEFAULT_SOURCE_DIR='~/CQT-experiments/data'
DEFAULT_REPORTING_HOST="cqtreporting.tortuga"
DEFAULT_REPORTING_DIR="/opt/cqt-reporting/data"

if [[ $# -eq 0 ]]; then
    # Use defaults
    SOURCE_HOST="$DEFAULT_SOURCE_HOST"
    SOURCE_DIR="$DEFAULT_SOURCE_DIR"
    REPORTING_HOST="$DEFAULT_REPORTING_HOST"
    REPORTING_DIR="$DEFAULT_REPORTING_DIR"
elif [[ $# -eq 4 ]]; then
    SOURCE_HOST="$1"
    SOURCE_DIR="$2"
    REPORTING_HOST="$3"
    REPORTING_DIR="$4"
else
    echo "Usage: $0 [--propagate] [SOURCE_HOST SOURCE_DIR REPORTING_HOST REPORTING_DIR]"
    exit 1
fi

echo "SOURCE_HOST:     $SOURCE_HOST"
echo "SOURCE_DIR:      $SOURCE_DIR"
echo "REPORTING_HOST:  $REPORTING_HOST"
echo "REPORTING_DIR:   $REPORTING_DIR"

# --- Create temporary directory (auto-cleaned) ---
TMP_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "Using temp dir: $TMP_DIR"

# --- Step 1: rsync NQCH -> local temp ---
# Trailing / on SOURCE_DIR means "copy *contents* of SOURCE_DIR into TMP_DIR"
echo "Syncing from ${SOURCE_HOST}:${SOURCE_DIR} to local temp..."
rsync -av -e ssh --delete \
    "${SOURCE_HOST}:${SOURCE_DIR%/}/" \
    "${TMP_DIR}/"

# --- Step 2: backup REPORTING directory ---
echo "Creating backup on REPORTING machine..."

BACKUP_PARENT_CMD="dirname \"$REPORTING_DIR\""
BACKUP_NAME_CMD="basename \"$REPORTING_DIR\""

BACKUP_PARENT="$(ssh "$REPORTING_HOST" "$BACKUP_PARENT_CMD")"
BACKUP_NAME="$(ssh "$REPORTING_HOST" "$BACKUP_NAME_CMD")"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

BACKUP_FILE="${BACKUP_NAME}_backup_${TIMESTAMP}.tar.gz"

ssh "$REPORTING_HOST" "
    set -e;
    cd \"$BACKUP_PARENT\";
    tar -czf \"$BACKUP_FILE\" \"$BACKUP_NAME\"
"

echo "Backup created on ${REPORTING_HOST}:${BACKUP_PARENT}/${BACKUP_FILE}"

# --- Step 3: temp -> REPORTING with correct overwrite behavior ---
RSYNC_DEST_OPTS=(-av -e ssh)

if [[ "$PROPAGATE_CHANGES" == false ]]; then
    echo "Mode: non-destructive (no overwrite of existing files)."
    RSYNC_DEST_OPTS+=(--ignore-existing)
else
    echo "Mode: propagate changes (overwrite modified files)."
    # no --ignore-existing => rsync overwrites if different (backup already done)
fi

echo "Syncing local temp to ${REPORTING_HOST}:${REPORTING_DIR}..."
rsync "${RSYNC_DEST_OPTS[@]}" \
    "${TMP_DIR}/" \
    "${REPORTING_HOST}:${REPORTING_DIR%/}/"

echo "Done."