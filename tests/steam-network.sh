#!/usr/bin/env bash
# Run inside the image with networking enabled. No credentials or game downloads.
set -euo pipefail
LOG=$(mktemp)
trap 'rm -f -- "$LOG"' EXIT

timeout 60s /steamcmd/steamcmd.sh \
    +@ShutdownOnFailedCommand 1 \
    +@NoPromptForPassword 1 \
    +login anonymous \
    +quit </dev/null 2>&1 | tee "$LOG"

python3 - "$LOG" <<'PY'
from pathlib import Path
import re
import sys

log = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
log = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", log)
if "/steamcmd/linux64/steamcmd" not in log:
    sys.exit("Steam connectivity check did not run the 64-bit client")
if not re.search(r"Waiting for user info\.\.\.\s*OK", log):
    sys.exit("SteamCMD did not complete its anonymous connection")
print("SteamCMD 64-bit anonymous connection passed.")
PY
