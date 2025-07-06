#!/usr/bin/env bash
set -euo pipefail

# Vérifs…
: "${STEAM_USER:?}"
: "${STEAM_PASS:?}"
: "${STEAM_SHARED_SECRET:?}"
: "${CONTENT_PATH:?}"
: "${PREVIEW_FILE:?}"
: "${PUBLISHED_FILE_ID:?}"
: "${TITLE:?}"
: "${DESCRIPTION:?}"
: "${VISIBILITY:?}"
# CHANGE_NOTE est optionnel


export STEAM_GUARD
STEAM_GUARD=$(python3 /app/otp.py)
echo "Using Steam Guard: $STEAM_GUARD"

# 1) Copie du contenu en écriture
TMP_CONTENT=$(mktemp -d)
echo "→ Copying content to temp dir: $TMP_CONTENT"
cp -r "${CONTENT_PATH}/." "$TMP_CONTENT/"

# 2) Override du addon.json dans le tmp
cat > "$TMP_CONTENT/addon.json" <<EOF
{
  "title":  "${TITLE//\"/\\\"}",
  "type":   "ServerContent",
  "tags":   ["fun","roleplay"],
  "ignore": ["*.git*","*.md","*.yml","*.yaml"]
}
EOF
echo "→ Forced addon.json for packaging:"
cat "$TMP_CONTENT/addon.json"
echo

# 3) Création du .gma
GMA=/tmp/addon.gma
echo "Creating GMA from '$TMP_CONTENT'…"
gmad create -folder "$TMP_CONTENT" -out "$GMA"

# 4) Préparation du VDF (via template + envsubst)
cat > /tmp/workshop.vdf.tpl <<'VDF'
"workshopitem"
{
    "appid"           "4000"
    "publishedfileid" "${PUBLISHED_FILE_ID}"
    "contentfolder"   "${GMA}"
    "previewfile"     "${PREVIEW_FILE}"
    "visibility"      "${VISIBILITY}"
    "title"           "${TITLE}"
    "description"     "${DESCRIPTION}"
    "changenote"      "${CHANGE_NOTE}"
}
VDF
export GMA=/tmp/addon.gma
envsubst < /tmp/workshop.vdf.tpl > /tmp/workshop_item.vdf

echo "Manifest ready:"
cat /tmp/workshop_item.vdf

# 5) Upload via SteamCMD
echo "Publishing to Workshop…"
/steamcmd/steamcmd.sh -console -debug \
  +login "$STEAM_USER" "$STEAM_PASS" "$STEAM_GUARD" \
  +workshop_build_item /tmp/workshop_item.vdf \
  +quit

echo "Done."
