# GMod Workshop Uploader

A lightweight Docker + SteamCMD-based uploader for automating Garry’s Mod Workshop addon publication and updates, with built-in Steam Guard (2FA) support via a small Python script.

---

## 📁 Repository Layout

```bash
.
├── Dockerfile
├── entrypoint.sh
├── example_addon/
│   ├── lua/
│   │   └── autorun/example_addon.lua
│   └── materials/example_addon/logo.png
├── otp.py
├── github-action.yml
└── README.md
```

-   **Dockerfile**  
    Builds an Ubuntu container with SteamCMD and your `entrypoint.sh`.
-   **entrypoint.sh**  
    Logs into SteamCMD, builds (or updates) the Workshop item using your mounted folder.
-   **example_addon/**  
    Sample addon folder (your real addon goes here).
-   **otp.py**  
    Generates the current 5-character Steam Guard code from your `STEAM_SHARED_SECRET`.
-   **github-action.yml**  
    GitHub Actions workflow that builds the image, generates the OTP, and publishes on each push.

---

## ⚙️ Prerequisites

-   **Docker** installed locally or in your CI environment.
-   **Python 3.x** (to run `otp.py`).
-   A **Steam account** with Mobile Authenticator enabled (non-limited) and your **shared_secret** exported.
    -   You must have spent at least US $5 on Steam to publish **public** Workshop items.

---

## 🚀 Local Setup & Manual Upload

1. **Build the Docker image**

    ```bash
    docker build -t gmod-uploader .
    ```

2. **Prepare your Python environment** (once)

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install steampy
    ```

3. **Export your secrets**

    ```bash
    export STEAM_USER="your_steam_username"
    export STEAM_PASS="your_steam_password"
    export STEAM_SHARED_SECRET="…your_shared_secret…"
    export NEW_VERSION="1.0.0"                        # bump as needed
    export GITHUB_REPOSITORY="user/repo"             # for links in description
    export NEW_TAG="v1.0.0"
    ```

4. **Generate a Steam Guard code**

    ```bash
    export STEAM_GUARD=$(python3 otp.py)
    echo "Using Steam Guard: $STEAM_GUARD"
    ```

5. **Run the Docker uploader**

    ```bash
    docker run --rm \
      -e STEAM_USER="$STEAM_USER" \
      -e STEAM_PASS="$STEAM_PASS" \
      -e STEAM_GUARD="$STEAM_GUARD" \
      -e CONTENT_PATH="/data" \
      -e TITLE="My Addon v1.2.3" \
      -e DESCRIPTION="Full changelog at https://github.com/…/releases/tag/v1.2.3" \
      -e CHANGE_NOTE="– Fixed crash on load – Added new feature X – Updated translations" \
      -e VISIBILITY="0" \
      -e PREVIEW_FILE="/data/materials/…/logo.png" \
      -e PUBLISHED_FILE_ID="123456789" \
      -v "$(pwd)/my-addon":/data \
      gmod-uploader
    ```

    - `PUBLISHED_FILE_ID=0` creates a **new** item.
    - To update, set `PUBLISHED_FILE_ID` to the ID returned on first run.

---

## 🤖 CI/CD with GitHub Actions

Your `.github/workflows/github-action.yml` is already configured to:

1. **Checkout** your repo on pushes to `main`.
2. **Build** the `gmod-uploader` image.
3. **Set up Python**, install `steampy`, and run `otp.py` to generate the OTP.
4. **Run** the Docker uploader step with the generated `STEAM_GUARD`.

Make sure you’ve added these **secrets** in your repository settings:

-   `STEAM_USER`
-   `STEAM_PASS`
-   `STEAM_SHARED_SECRET`
-   `ADDON_ID` (your Workshop item ID; set to `0` for initial publication)

You can trigger manually via **workflow_dispatch** or on every push to `main`.

---

## 🔑 Environment Variables

| Variable                 | Description                                                              | Notes                     |
| ------------------------ | ------------------------------------------------------------------------ | ------------------------- |
| `STEAM_USER`             | Your Steam account username                                              | —                         |
| `STEAM_PASS`             | Your Steam account password                                              | —                         |
| `STEAM_SHARED_SECRET`    | The Mobile Auth shared secret (for TOTP)                                 | —                         |
| `STEAM_GUARD`            | Generated 2FA code (injected via `otp.py`)                               | auto-generated            |
| `CONTENT_PATH`           | Path inside container to your addon folder                               | `/data`                   |
| `TITLE`                  | Workshop item title (e.g. `example-addon v1.0.0`)                        | —                         |
| `DESCRIPTION`            | Workshop description, e.g. link to GitHub Release                        | —                         |
| `VISIBILITY`             | `0=public`, `1=friends only`, `2=private`                                | `0` (public)              |
| `PREVIEW_FILE`           | Full path (in container) to your preview image, e.g. `/data/...png`      | Required for public items |
| `PUBLISHED_FILE_ID`      | Workshop published file ID (`0` to create new, or existing ID to update) | `0`                       |
| `NEW_VERSION`, `NEW_TAG` | Used for dynamic titles/descriptions in CI                               | —                         |

---

## ❗️ Notes

-   Steam **requires** a valid **preview image** and a non-empty content folder to publish or change visibility to public.
-   Limited Steam accounts (no purchase) cannot publish **public** Workshop items.
-   Keep your `shared_secret` safe—do not commit it. Use CI secrets.

Happy automating your GMod Workshop uploads! 🚀
