#!/usr/bin/env bash
set -euo pipefail
umask 077

APP_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
TOTAL_START=$SECONDS
: "${CONTENT_PATH:?Please set CONTENT_PATH}"
: "${TITLE:?Please set TITLE}"
: "${DESCRIPTION:?Please set DESCRIPTION}"
export PUBLISHED_FILE_ID="${PUBLISHED_FILE_ID:-0}"
export VISIBILITY="${VISIBILITY:-0}"
export CHANGE_NOTE="${CHANGE_NOTE:-}"
DRY_RUN="${DRY_RUN:-false}"

fail() { echo "Error: $*" >&2; exit 1; }
timing() { echo "Timing: $1 = $((SECONDS - $2))s"; }

[[ -d "$CONTENT_PATH" ]] || fail "CONTENT_PATH must be a directory"
[[ "$PUBLISHED_FILE_ID" =~ ^[0-9]+$ ]] || fail "PUBLISHED_FILE_ID must be numeric"
[[ "$VISIBILITY" =~ ^[012]$ ]] || fail "VISIBILITY must be 0 (public), 1 (friends), or 2 (private)"
[[ "$DRY_RUN" == true || "$DRY_RUN" == false ]] || fail "DRY_RUN must be true or false"
if [[ -n "${PREVIEW_FILE:-}" ]]; then
    [[ -f "$PREVIEW_FILE" ]] || fail "PREVIEW_FILE does not exist"
elif [[ "$PUBLISHED_FILE_ID" =~ ^0+$ ]]; then
    fail "PREVIEW_FILE is required when creating a new Workshop item"
fi
if [[ "$DRY_RUN" != true ]]; then
    : "${STEAM_USER:?Please set STEAM_USER}"
    : "${STEAM_PASS:?Please set STEAM_PASS}"
    [[ -n "${STEAM_GUARD:-}" || -n "${STEAM_SHARED_SECRET:-}" ]] \
        || fail "Set STEAM_GUARD or STEAM_SHARED_SECRET"
fi

WORK_DIR=$(mktemp -d)
trap 'rm -rf -- "$WORK_DIR"' EXIT
mkdir "$WORK_DIR/content"
GMA="$WORK_DIR/content/addon.gma"
MANIFEST="$WORK_DIR/workshop_item.vdf"

STEP_START=$SECONDS
if [[ -f "$CONTENT_PATH/addon.json" ]]; then
    # gmad only reads its source folder, so a read-only mount is sufficient.
    PACKAGE_SOURCE="$CONTENT_PATH"
    echo "Using existing addon.json; packaging directly from source."
else
    PACKAGE_SOURCE="$WORK_DIR/source"
    mkdir "$PACKAGE_SOURCE"
    # Reflink when supported; fall back to a normal copy on other filesystems.
    cp -a --reflink=auto "$CONTENT_PATH/." "$PACKAGE_SOURCE/"
    python3 "$APP_DIR/workshop.py" addon "$PACKAGE_SOURCE/addon.json"
    echo "Generated default addon.json in temporary content."
fi
timing "content preparation" "$STEP_START"

STEP_START=$SECONDS
gmad create -folder "$PACKAGE_SOURCE" -out "$GMA" -quiet
[[ -s "$GMA" ]] || fail "gmad did not produce a non-empty archive"
timing "GMA packaging" "$STEP_START"
echo "GMA size: $(stat -c %s "$GMA") bytes"
python3 "$APP_DIR/workshop.py" manifest "$WORK_DIR/content" "$MANIFEST"

if [[ "$DRY_RUN" == true ]]; then
    echo "Dry run: archive and manifest validated; SteamCMD was not started."
    timing "total" "$TOTAL_START"
    exit 0
fi

# Generate only after packaging. An explicitly supplied code takes precedence.
if [[ -z "${STEAM_GUARD:-}" ]]; then
    echo "Steam Guard source: automatic code from shared secret."
    STEAM_GUARD=$(python3 "$APP_DIR/otp.py")
else
    echo "Steam Guard source: manually supplied code."
fi
if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
    echo "::add-mask::$STEAM_GUARD"
fi

STEP_START=$SECONDS
echo "Connecting to Steam and publishing to Workshop…"
# SteamCMD can return zero after a failed upload. Require its success message too.
# Noninteractive mode prevents a missing/expired Guard code from hanging CI.
STEAM_STATUS=0
/steamcmd/steamcmd.sh \
    +@ShutdownOnFailedCommand 1 \
    +@NoPromptForPassword 1 \
    +login "$STEAM_USER" "$STEAM_PASS" "$STEAM_GUARD" \
    +workshop_build_item "$MANIFEST" \
    +quit </dev/null 2>&1 | tee "$WORK_DIR/steamcmd.log" || STEAM_STATUS=$?
timing "Steam connection and upload" "$STEP_START"
[[ "$STEAM_STATUS" -eq 0 ]] || fail "SteamCMD exited with status $STEAM_STATUS"
ITEM_ID=$(python3 "$APP_DIR/workshop.py" result "$WORK_DIR/steamcmd.log" "$MANIFEST")
echo "Published Workshop item: $ITEM_ID"
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "published_file_id=$ITEM_ID" >> "$GITHUB_OUTPUT"
fi
timing "total" "$TOTAL_START"
