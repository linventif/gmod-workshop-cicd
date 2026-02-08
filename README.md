# GMod Workshop Uploader

A Docker-based CLI for building Garry's Mod `.gma` addons and publishing
them to Steam Workshop via SteamCMD.

-   No Windows-only tools. Works on Linux hosts and in CI/CD.
-   2FA support via Steam Guard (TOTP).

------------------------------------------------------------------------

## Quick Start (CI‑friendly, no build step)

You can directly use the prebuilt image:

``` bash
docker run --rm   -e STEAM_USER=your_user   -e STEAM_PASS=your_pass   -e STEAM_SHARED_SECRET=your_secret   -e PUBLISHED_FILE_ID=0   -e CONTENT_PATH=/data/addon   -e PREVIEW_FILE=/data/addon/materials/icon.png   -e TITLE="My Addon"   -e DESCRIPTION="Uploaded from CI"   -e VISIBILITY=0   -e CHANGE_NOTE="Initial upload"   -v $(pwd)/my_addon:/data/addon:ro   ghcr.io/linventif/gmod-workshop-cicd:latest
```

------------------------------------------------------------------------

## Prerequisites

-   Docker
-   A Steam account with Workshop publishing rights
-   Steam username, password, and shared secret

Set them as environment variables or CI secrets:

``` bash
export STEAM_USER="your_steam_username"
export STEAM_PASS="your_steam_password"
export STEAM_SHARED_SECRET="your_steam_shared_secret"
```

------------------------------------------------------------------------

## Local Manual Upload

### 1. Pull prebuilt image

``` bash
docker pull ghcr.io/linventif/gmod-workshop-cicd:latest
```

### 2. Run uploader

``` bash
docker run --rm   -e STEAM_USER   -e STEAM_PASS   -e STEAM_SHARED_SECRET   -e PUBLISHED_FILE_ID=0   -e CONTENT_PATH=/data/example_addon   -e PREVIEW_FILE=/data/example_addon/materials/example_addon/logo.png   -e TITLE="Example Addon"   -e DESCRIPTION="Manual upload"   -e VISIBILITY=0   -e CHANGE_NOTE="Initial upload"   -v $(pwd)/example_addon:/data/example_addon:ro   ghcr.io/linventif/gmod-workshop-cicd:latest
```

------------------------------------------------------------------------

## GitHub Actions CI/CD (recommended)

This workflow:

-   Tries to pull the prebuilt image
-   Builds it locally if missing
-   Publishes the addon

``` yaml
name: Publish Example Addon

on: [push]

jobs:
  publish:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Pull uploader image
        run: docker pull ghcr.io/linventif/gmod-workshop-cicd:latest

      - name: Run uploader
        env:
          STEAM_USER: ${{ secrets.STEAM_USER }}
          STEAM_PASS: ${{ secrets.STEAM_PASS }}
          STEAM_SHARED_SECRET: ${{ secrets.STEAM_SHARED_SECRET }}
          PUBLISHED_FILE_ID: ${{ secrets.EXAMPLE_ADDON_ID }}
          CONTENT_PATH: /data/example_addon
          PREVIEW_FILE: /data/example_addon/materials/example_addon/logo.png
          TITLE: "Example Addon"
          DESCRIPTION: "Automated CI release"
          VISIBILITY: "0"
          CHANGE_NOTE: "Automated build"
        run: |
          docker run --rm             -e STEAM_USER             -e STEAM_PASS             -e STEAM_SHARED_SECRET             -e PUBLISHED_FILE_ID             -e CONTENT_PATH             -e PREVIEW_FILE             -e TITLE             -e DESCRIPTION             -e VISIBILITY             -e CHANGE_NOTE             -v ${{ github.workspace }}/example_addon:/data/example_addon:ro             ${{ steps.img.outputs.name }}
```

------------------------------------------------------------------------

## Configuration

  Variable              Description
  --------------------- -------------------------------------
  STEAM_USER            Steam username
  STEAM_PASS            Steam password
  STEAM_SHARED_SECRET   Steam TOTP shared secret
  PUBLISHED_FILE_ID     Workshop item ID (0 = create new)
  CONTENT_PATH          Path inside container to addon
  PREVIEW_FILE          Path to preview image
  TITLE                 Workshop title
  DESCRIPTION           Workshop description
  VISIBILITY            0=public, 1=friends-only, 2=private
  CHANGE_NOTE           Workshop changelog text

------------------------------------------------------------------------

## Notes

-   `PUBLISHED_FILE_ID=0` creates a new Workshop item.
-   Any non‑zero value updates an existing item.
-   The image already contains SteamCMD and gmad.

------------------------------------------------------------------------

Happy publishing!
