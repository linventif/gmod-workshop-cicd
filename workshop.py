#!/usr/bin/env python3
"""Serialize addon metadata and SteamCMD KeyValues without shell substitution."""

import json
import os
from pathlib import Path
import re
import sys


def vdf_quote(value):
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError("VDF values cannot contain control characters")
    return '"' + (value.replace("\\", "\\\\").replace('"', '\\"')
                  .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")) + '"'


def write_addon(path):
    metadata = {
        "title": os.environ["TITLE"],
        "type": "ServerContent",
        "tags": ["fun", "roleplay"],
        "ignore": ["*.git*", "*.md", "*.yml", "*.yaml"],
    }
    Path(path).write_text(json.dumps(metadata, ensure_ascii=False) + "\n", encoding="utf-8")


def write_manifest(content_folder, path):
    values = {
        "appid": "4000",
        "publishedfileid": os.environ.get("PUBLISHED_FILE_ID", "0"),
        "contentfolder": str(Path(content_folder).resolve()),
        "visibility": os.environ.get("VISIBILITY", "0"),
        "title": os.environ["TITLE"],
        "description": os.environ["DESCRIPTION"],
        "changenote": os.environ.get("CHANGE_NOTE", ""),
    }
    preview = os.environ.get("PREVIEW_FILE", "")
    if preview:
        values["previewfile"] = str(Path(preview).resolve())
    lines = ["\"workshopitem\"", "{"]
    lines.extend(f"    {vdf_quote(key)} {vdf_quote(value)}" for key, value in values.items())
    Path(path).write_text("\n".join([*lines, "}", ""]), encoding="utf-8")


def published_id(log_path, manifest_path):
    text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    # workshop_build_item prints a standalone "Success." and writes the ID back
    # into its VDF. Creation alone is not confirmation that the upload succeeded.
    if not re.search(r"^\s*Success\.\s*$", text, re.MULTILINE):
        raise ValueError("SteamCMD did not confirm publication; inspect its output above")
    manifest = Path(manifest_path).read_text(encoding="utf-8")
    matches = re.findall(r'^\s*"publishedfileid"\s+"(\d+)"\s*$', manifest, re.MULTILINE | re.IGNORECASE)
    if len(matches) != 1 or int(matches[0]) == 0:
        raise ValueError("SteamCMD did not write a valid publishedfileid to the manifest")
    expected = os.environ.get("PUBLISHED_FILE_ID", "0")
    if int(expected) and int(matches[0]) != int(expected):
        raise ValueError("SteamCMD returned a different Workshop item ID")
    return matches[0]


if __name__ == "__main__":
    try:
        if sys.argv[1] == "addon":
            write_addon(sys.argv[2])
        elif sys.argv[1] == "manifest":
            write_manifest(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "result":
            print(published_id(sys.argv[2], sys.argv[3]))
        else:
            raise ValueError("Unknown command")
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
