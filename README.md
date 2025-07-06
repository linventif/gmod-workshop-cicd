# GMod Workshop Uploader

A Docker-based CLI for building Garry’s Mod `.gma` addons and publishing them to Steam Workshop via SteamCMD.

-   **No Windows-only tools.** Works on Linux hosts and in CI/CD.
-   **2FA support.** Generates Steam Guard codes automatically via [steampy](https://pypi.org/project/steampy/).
-   **Full CI/CD example** using GitHub Actions included.

---

## Contents

-   [GMod Workshop Uploader](#gmod-workshop-uploader)
    -   [Contents](#contents)
    -   [Prerequisites](#prerequisites)
    -   [Local Manual Upload](#local-manual-upload)
    -   [GitHub Actions CI/CD](#github-actions-cicd)
        -   [Example Workflow](#example-workflow)
    -   [Configuration](#configuration)
    -   [FAQ](#faq)

---

## Prerequisites

-   Docker (Host or Runner)
-   A Steam account with **Workshop Publisher** privileges.
-   Your Steam **username**, **password**, and **shared_secret** (for TOTP).

Store sensitive values in environment variables or CI secrets:

```bash
export STEAM_USER="your_steam_username"
export STEAM_PASS="your_steam_password"
export STEAM_SHARED_SECRET="your_steam_shared_secret"
```

---

## Local Manual Upload

1. **Build the Docker image** (run from repo root):

    ```bash
    docker build -t gmod-uploader .
    ```

2. **Generate a Steam Guard code** (requires Python & `steampy`):

    ```bash
    pip install --user steampy
    python3 - <<EOF
    from steampy.guard import generate_one_time_code
    import os
    print(generate_one_time_code(os.environ['STEAM_SHARED_SECRET']))
    EOF
    ```

3. **Run the uploader**:

    ```bash
    export STEAM_GUARD=<code-from-step-2>
    docker run --rm       -e STEAM_USER       -e STEAM_PASS       -e STEAM_SHARED_SECRET       -e STEAM_GUARD       -e PUBLISHED_FILE_ID="0"       -e CONTENT_PATH="/data/example_addon"       -e PREVIEW_FILE="/data/example_addon/materials/example_addon/logo.png"       -e TITLE="Example Addon v1.0.0"       -e DESCRIPTION="Continuous integration for Garry’s Mod example_addon"       -e VISIBILITY="0"       -e CHANGE_NOTE="Initial manual upload"       -v "$(pwd)/example_addon":/data/example_addon:ro       gmod-uploader
    ```

-   `PUBLISHED_FILE_ID=0` creates a **new** Workshop item.
-   To **update** an existing item, set `PUBLISHED_FILE_ID` to your item’s ID.

---

## GitHub Actions CI/CD

Automate builds and uploads on every push to `main` (or manual dispatch).

### Example Workflow

```yaml
name: Publish Example Addon

on: [push]

permissions:
  contents: write

jobs:
  publish:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build gmod-uploader image
        run: docker build -t gmod-uploader .

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install steampy
        run: pip install steampy

      - name: Generate Steam Guard OTP
        # writes STEAM_GUARD into GITHUB_ENV
        run: |
          echo "STEAM_GUARD=$(python3 otp.py)" >> $GITHUB_ENV

      - name: Publish example_addon to Workshop
        env:
          STEAM_USER:         ${{ secrets.STEAM_USER }}
          STEAM_PASS:         ${{ secrets.STEAM_PASS }}
          STEAM_SHARED_SECRET:${{ secrets.STEAM_SHARED_SECRET }}
          STEAM_GUARD:        ${{ env.STEAM_GUARD }}
          PUBLISHED_FILE_ID:  ${{ secrets.EXAMPLE_ADDON_ID }}  # e.g. 3518398536
          CONTENT_PATH:       /data/example_addon
          PREVIEW_FILE:       /data/example_addon/materials/example_addon/logo.png
          TITLE:              'Example Addon v1.0.0'
          DESCRIPTION:        'Continuous integration for Garry’s Mod example_addon'
          VISIBILITY:         '0'                      # 0=public,1=friends-only,2=private
          CHANGE_NOTE:        'Automated CI/CD release'
        run: |
          docker run --rm             -e STEAM_USER             -e STEAM_PASS             -e STEAM_SHARED_SECRET             -e STEAM_GUARD             -e PUBLISHED_FILE_ID             -e CONTENT_PATH             -e PREVIEW_FILE             -e TITLE             -e DESCRIPTION             -e VISIBILITY             -e CHANGE_NOTE             -v ${{ github.workspace }}/example_addon:/data/example_addon:ro             gmod-uploader
```

> **Tip:** Place this file under `.github/workflows/` to enable proper YAML validation in VS Code.

---

## Configuration

| Variable              | Description                                                             |
| --------------------- | ----------------------------------------------------------------------- |
| `STEAM_USER`          | Your Steam username (stored as a secret).                               |
| `STEAM_PASS`          | Your Steam password (stored as a secret).                               |
| `STEAM_SHARED_SECRET` | Your TOTP shared secret (from Desktop Authenticator or mobile export).  |
| `STEAM_GUARD`         | Generated OTP code (from `otp.py` or via `steampy`).                    |
| `PUBLISHED_FILE_ID`   | Workshop item ID (`0` to create new, or your existing ID to update).    |
| `CONTENT_PATH`        | **Inside container** path to addon folder (e.g. `/data/example_addon`). |
| `PREVIEW_FILE`        | Path to your 512×512 JPEG icon inside `CONTENT_PATH`.                   |
| `TITLE`               | Workshop title.                                                         |
| `DESCRIPTION`         | Workshop description (Markdown).                                        |
| `VISIBILITY`          | `0=public`, `1=friends-only`, `2=private`.                              |
| `CHANGE_NOTE`         | The Steam Workshop “changenote” field (shown in update history).        |

---

## FAQ

**Q: Why add `addon.json`?**  
A: GMod 13+ requires `addon.json` at the root to whitelist files and define metadata. The uploader will inject or override it if mounted read-only.

**Q: Editor flags `${{ secrets.… }}` as invalid?**  
A: Move your workflow under `.github/workflows/` to load the official GitHub schema and eliminate warnings.

**Q: How to handle version bumps automatically?**  
A: See our [Auto Release example](#) using Git tags, changelog generation, and multiple release targets (GitHub, GModStore, Workshop).

---

Happy publishing!  
For more on Workshop rules & folder whitelist, see Steam’s official guide:  
https://developer.valvesoftware.com/wiki/Workshop_Addon_Updating
