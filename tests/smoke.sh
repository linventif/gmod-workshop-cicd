#!/usr/bin/env bash
# Run inside the built image, with the repository at /workspace and networking off.
set -euo pipefail
WORK=$(mktemp -d)
trap 'rm -rf -- "$WORK"' EXIT
export CONTENT_PATH=/workspace/tests/fixtures/addon
export TITLE='Example "Addon"'
export DESCRIPTION=$'Test description\nwith "quotes" and \\slashes'
export PUBLISHED_FILE_ID=12345

# Verify the real launcher selects the native client before replacing it below.
timeout 30s /steamcmd/steamcmd.sh +quit > "$WORK/startup.log" 2>&1
if [[ "$(cat "$WORK/startup.log")" != *'/steamcmd/linux64/steamcmd'* ]]; then
    cat "$WORK/startup.log" >&2
    echo 'SteamCMD did not start its 64-bit client' >&2
    exit 1
fi

# Exercise the production entrypoint against a read-only source, without credentials.
DRY_RUN=true bash /app/entrypoint.sh

# Round-trip actual archive bytes through the standalone official gmad binary.
gmad create -folder "$CONTENT_PATH" -out "$WORK/addon.gma" -quiet
gmad extract -file "$WORK/addon.gma" -out "$WORK/extracted" -quiet
cmp "$CONTENT_PATH/lua/autorun/smoke.lua" "$WORK/extracted/lua/autorun/smoke.lua"
cmp "$CONTENT_PATH/materials/smoke.vmt" "$WORK/extracted/materials/smoke.vmt"

# Compatibility fallback: generate metadata in temporary storage, leave source untouched.
mkdir -p "$WORK/source/lua"
cp "$CONTENT_PATH/lua/autorun/smoke.lua" "$WORK/source/lua/test.lua"
CONTENT_PATH="$WORK/source" DRY_RUN=true bash /app/entrypoint.sh
[[ ! -e "$WORK/source/addon.json" ]]

# Replace SteamCMD only in this disposable, offline container.
# A manual code must win even when the shared secret is intentionally invalid.
cat > /steamcmd/steamcmd.sh <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
[[ "$*" == *"+login test-user test-pass ${EXPECTED_GUARD:-MANUAL}"* ]]
# Check the actual manifest provided to SteamCMD, including its content directory.
while [[ "$1" != +workshop_build_item ]]; do shift; done
python3 - "$2" <<'PY'
import json
from pathlib import Path
import re
import sys
tokens = re.findall(r'"(?:[^"\\]|\\.)*"', Path(sys.argv[1]).read_text())
tokens = [json.loads(token) for token in tokens][1:]
values = dict(zip(tokens[::2], tokens[1::2]))
folder = Path(values['contentfolder'])
assert folder.is_dir()
assert [item.name for item in folder.iterdir()] == ['addon.gma']
assert 'previewfile' not in values
PY
if [[ "${MOCK_FAILURE:-false}" == true ]]; then
    echo 'ERROR! Failed to update workshop item'
    exit 0
fi
echo 'Success.'
STUB
export STEAM_USER=test-user STEAM_PASS=test-pass STEAM_GUARD=MANUAL
export STEAM_SHARED_SECRET=intentionally-invalid
export GITHUB_OUTPUT="$WORK/outputs"
bash /app/entrypoint.sh
[[ "$(cat "$GITHUB_OUTPUT")" == published_file_id=12345 ]]

if MOCK_FAILURE=true bash /app/entrypoint.sh; then
    echo 'Uploader accepted a SteamCMD failure with exit status zero' >&2
    exit 1
fi

# Automatic generation runs only after a real archive exists, and is never logged.
# Replace just the generator in this disposable container to avoid TOTP clock races.
cat > /app/otp.py <<'PY'
from pathlib import Path
import os
assert list(Path(os.environ['TMPDIR']).glob('*/content/addon.gma'))
print('AUTO2')
PY
mkdir "$WORK/auto"
STEAM_GUARD='' EXPECTED_GUARD=AUTO2 TMPDIR="$WORK/auto" bash /app/entrypoint.sh > "$WORK/auto.log"
if [[ "$(cat "$WORK/auto.log")" == *AUTO2* ]]; then
    echo 'Uploader printed an automatic Steam Guard code' >&2
    exit 1
fi
[[ -z "$(ls -A "$WORK/auto")" ]]
if CONTENT_PATH="$WORK/missing" DRY_RUN=true bash /app/entrypoint.sh; then
    echo 'Uploader accepted a missing source directory' >&2
    exit 1
fi
if PUBLISHED_FILE_ID=0 DRY_RUN=true bash /app/entrypoint.sh; then
    echo 'Uploader accepted item creation without a preview' >&2
    exit 1
fi
echo 'Offline smoke tests passed.'
