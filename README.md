# GMod Workshop Uploader

Build Garry's Mod `.gma` addons and publish them to Steam Workshop using SteamCMD.
Linux / amd64 only.

## What makes this pipeline faster

- **No Garry's Mod server download.** The Docker build compiles the standalone
  [official gmad source](https://github.com/Facepunch/gmad) and its
  [Bootil dependency](https://github.com/garrynewman/bootil) at pinned revisions.
  Only the resulting binary enters the runtime image.
- SteamCMD is initialized while building the image. It can still check for updates
  when started, but each publication no longer starts with an uninitialized installer.
- The runtime selects SteamCMD's native 64-bit client using the official launcher's
  `STEAM_PLATFORM=linux64` setting. This avoids the 32-bit `socketcall` failure on
  affected Docker runners while retaining Docker's default security settings.
- GitHub Actions reuses an image tagged with a hash of the Dockerfile and runtime
  sources. An addon-only change skips image construction entirely.
- New images use a persistent
  [BuildKit cache](https://docs.docker.com/build/ci/github-actions/cache/) and pass
  offline packaging tests before being pushed.
- An existing `addon.json` allows packaging directly from the read-only source
  directory. No full content copy is needed.
- One workflow coordinates image preparation and publication, using an immutable
  image digest. A single push cannot trigger the old push + workflow_run duplicate.

A first build still downloads build dependencies, small source archives and SteamCMD.
It never installs the dedicated server. Build tools, source trees, pip and Python
third-party packages are absent from the runtime image.

Measured on 2026-11-20: the previously published image at digest
`sha256:920e3a0b5e1ccd02ba12a22b886f61b93c0bb4772dc04d01699496327875bb64`
has 4,113,581,147 bytes of compressed layers. The new local OCI image is
approximately 157 MB: **96% less data to download** on a cold runner.
This compares image transfer sizes, not end-to-end Workshop publication times.

## GitHub Actions

The included [publication workflow](.github/workflows/publish-example-addon.yml)
runs on relevant changes on `main`, or manually from `main`. README-only changes
do not publish anything.

Configure these repository secrets:

| Secret | Purpose |
| --- | --- |
| `STEAM_USER` | Steam login |
| `STEAM_PASS` | Steam password |
| `STEAM_SHARED_SECRET` | Base64 shared secret from your existing mobile authenticator |
| `EXAMPLE_ADDON_ID` | Existing Workshop item ID, greater than zero |

The workflow refuses a missing or zero item ID to prevent accidental creation of a
new item on every push. Create the initial item with the local command below, then
store its ID as `EXAMPLE_ADDON_ID`.

The [image workflow](.github/workflows/build-image.yml) is reusable and can also be
run manually. The publication job depends on its success and receives its resolved
`ghcr.io/OWNER/REPO@sha256:...` image reference. It never races a build of `latest`.
Grant the repository's Actions token access to its GHCR package if that package
already exists under different permissions.

Publications use a concurrency group with `cancel-in-progress: false`: an active
upload finishes before another starts. GitHub may replace older pending runs with
a newer pending run. Use the same group for workflows updating the same item, and
different groups for different items.

The separate [PR validation workflow](.github/workflows/validate.yml) runs unit tests,
builds the image and tests real GMA creation/extraction without Steam credentials.
Both PR validation and image builds check a real anonymous Steam connection.
New images must pass this check before being pushed to GHCR. PR validation does
not publish an image or a Workshop item.

Smoke tests use a tiny fixture addon, so they do not repeatedly package your real
content. The real addon is packaged once per publication and validated by gmad.

## Local publication

Build the image locally:

```bash
docker build -t gmod-workshop-cicd:local .
export UPLOADER_IMAGE=gmod-workshop-cicd:local
```

Alternatively, use `ghcr.io/linventif/gmod-workshop-cicd:latest` after the updated
image has been published. For reproducible deployments, use its `@sha256:...`
digest instead of `:latest`.

Supply credentials through your environment:

```bash
export STEAM_USER=your_login
export STEAM_PASS=your_password
export STEAM_SHARED_SECRET=your_authenticator_shared_secret
```

Update an existing item:

```bash
docker run --rm \
  -e STEAM_USER -e STEAM_PASS -e STEAM_SHARED_SECRET \
  -e PUBLISHED_FILE_ID=1234567890 \
  -e CONTENT_PATH=/data/addon \
  -e TITLE="My Addon" \
  -e DESCRIPTION="Uploaded from CI" \
  -e VISIBILITY=0 \
  -e CHANGE_NOTE="Updated addon" \
  -v "$PWD/example_addon:/data/addon:ro" \
  "$UPLOADER_IMAGE"
```

To create an item, set `PUBLISHED_FILE_ID=0` and add
`-e PREVIEW_FILE=/data/addon/materials/example_addon/logo.png`. The confirmed item ID
is printed after a successful upload. Reuse it for all subsequent updates.
An omitted preview on an update preserves the existing Workshop preview.

To supply a manual code, use `-e STEAM_GUARD` after exporting it. A supplied manual
code takes precedence over `STEAM_SHARED_SECRET`. Automatic codes are generated
after packaging, immediately before SteamCMD, using Steam's public server time.
The generator waits for a new 30-second window if less than 15 seconds remain.
Only clock offset and remaining validity are logged, never the code or secret.
If the Steam time endpoint is unavailable, generation stops with an explicit error.

## Configuration

| Variable / action input | Default | Purpose |
| --- | --- | --- |
| `STEAM_USER` / `steam_user` | Required for upload | Steam login |
| `STEAM_PASS` / `steam_pass` | Required for upload | Steam password |
| `STEAM_SHARED_SECRET` / `steam_shared_secret` | Conditional | Automatic Steam Guard; required unless a manual code is supplied |
| `STEAM_GUARD` / `steam_guard` | Empty | Manual code, preferred when supplied |
| `CONTENT_PATH` / `content_path` | Required | Addon directory |
| `PREVIEW_FILE` / `preview_file` | Empty | Preview image; required for creation, optional for updates |
| `PUBLISHED_FILE_ID` / `published_file_id` | `0` | Zero creates an item; a nonzero ID updates it |
| `TITLE` / `title` | Required | Workshop page title; also used for generated addon metadata |
| `DESCRIPTION` / `description` | Required | Workshop page description |
| `VISIBILITY` / `visibility` | `0` | `0` public, `1` friends, `2` private |
| `CHANGE_NOTE` / `change_note` | Empty | Update notes |
| `DRY_RUN` / `dry_run` | `false` | Package and validate without connecting to Steam |

An existing `addon.json` is preserved, including its title, type, tags and ignore
rules. `TITLE` still updates the Workshop page title independently. Invalid metadata
fails during packaging instead of being silently overwritten.

If `addon.json` is missing, the uploader copies content to temporary storage,
generates the former defaults (`ServerContent`, `fun`, `roleplay`) and leaves the
source untouched. Add this file to your addon to avoid that copy.

The Docker action in [action.yml](action.yml) keeps the prebuilt `:latest` image for
compatibility. Its `published_file_id` output is the ID confirmed by SteamCMD.
For digest-pinned publication, use the supplied workflow or a direct Docker command.

The manifest points to a temporary directory containing only `addon.gma`, following
the [SteamCMD content-folder format](https://partner.steamgames.com/doc/features/workshop/implementation#SteamCmd).
Titles, descriptions and notes are serialized with escaping for quotes, backslashes
and line breaks.

## Verification and timing

Run the unit tests:

```bash
python3 -m unittest discover -s tests -v
```

Test the built image, including GMA creation/extraction and simulated upload failures:

```bash
docker run --rm --network none \
  -v "$PWD:/workspace:ro" \
  --entrypoint bash "$UPLOADER_IMAGE" /workspace/tests/smoke.sh
```

Check Steam connectivity without credentials or publishing anything:

```bash
docker run --rm \
  -v "$PWD:/workspace:ro" \
  --entrypoint bash "$UPLOADER_IMAGE" /workspace/tests/steam-network.sh
```

The check requires outbound access to Steam and times out after 60 seconds.
`CreateBoundSocket ... (38)` followed by `No Connection` can indicate the
[32-bit Docker runner issue](https://github.com/actions/runner-images/issues/14790).
The startup log should show `/steamcmd/linux64/steamcmd` in the updated image.

Or validate your own addon with `DRY_RUN=true`; Steam credentials are unnecessary:

```bash
docker run --rm --network none \
  -e DRY_RUN=true -e PUBLISHED_FILE_ID=1234567890 \
  -e CONTENT_PATH=/data/addon -e TITLE="My Addon" -e DESCRIPTION="Validation" \
  -v "$PWD/example_addon:/data/addon:ro" \
  "$UPLOADER_IMAGE"
```

Logs report image pull time, image size, content preparation time, GMA packaging
time, GMA size, Steam connection/upload time and total uploader time.
Use those measurements on your real addon to compare before and after; Steam
authentication, network throughput and Workshop processing remain external costs.

SteamCMD must both exit successfully and confirm the Workshop commit. The uploader
also verifies the nonzero published file ID in the VDF, including that it matches
the requested item on updates. A zero exit status alone is insufficient. Uploads
are not automatically retried, which also avoids creating duplicate items after
an ambiguous network failure.
