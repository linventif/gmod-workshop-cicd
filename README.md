# Garry's Mod Workshop Deployment

This repository demonstrates how to automatically deploy Garry's Mod addons to the Steam Workshop using Docker and GitHub Actions.

## Overview

This CI/CD setup allows you to:

-   Automatically publish Garry's Mod addons to Steam Workshop
-   Use Docker for consistent deployment environment
-   Deploy on every push to main branch or manually trigger deployment
-   Update existing workshop items or create new ones

## Repository Structure

```text
├── Dockerfile              # Docker image for SteamCMD and workshop publishing
├── entrypoint.sh           # Script that handles the Steam Workshop publishing
├── github-action.yml       # GitHub Actions workflow for automated deployment
└── adn-test/              # Example Garry's Mod addon
    └── lua/
        └── autorun/
            └── adn_test.lua
```

## Setup Instructions

### 1. Configure GitHub Secrets

In your GitHub repository, go to **Settings > Secrets and variables > Actions** and add the following secrets:

-   `STEAM_USER`: Your Steam username
-   `STEAM_PASS`: Your Steam password
-   `ADN_TEST_PUBLISHED_FILE_ID`: Workshop item ID (set to `0` to create a new item)

### 2. Prepare Your Addon

Place your Garry's Mod addon files in the appropriate directory structure. For example:

```text
your-addon/
├── lua/
│   ├── autorun/
│   │   └── your_script.lua
│   └── entities/
└── materials/
```

### 3. Update GitHub Action Configuration

Modify the `github-action.yml` file to match your addon:

```yaml
- name: Publish adn-test to Workshop
  env:
      STEAM_USER: ${{ secrets.STEAM_USER }}
      STEAM_PASS: ${{ secrets.STEAM_PASS }}
      PUBLISHED_FILE_ID: ${{ secrets.ADN_TEST_PUBLISHED_FILE_ID }}
      CONTENT_PATH: /data/adn-test
      TITLE: 'ADN Test Addon'
      DESCRIPTION: 'Test addon for automated deployment'
      VISIBILITY: '0' # 0=public, 1=friends only, 2=private
  run: |
      docker run --rm \
        -e STEAM_USER \
        -e STEAM_PASS \
        -e CONTENT_PATH \
        -e TITLE \
        -e DESCRIPTION \
        -e VISIBILITY \
        -e PUBLISHED_FILE_ID \
        -v ${{ github.workspace }}/adn-test:/data/adn-test \
        gmod-uploader
```

## How It Works

### Docker Container

The `Dockerfile` creates a Ubuntu-based container with:

-   SteamCMD for Steam Workshop interactions
-   32-bit libraries required for SteamCMD
-   Proper environment setup for automated publishing

### Publishing Script

The `entrypoint.sh` script:

1. Validates required environment variables
2. Generates a VDF (Valve Data Format) file with workshop item metadata
3. Uses SteamCMD to publish or update the workshop item

### GitHub Actions Workflow

The workflow:

1. Triggers on pushes to main branch or manual dispatch
2. Builds the Docker image
3. Runs the container with your addon files mounted
4. Publishes to Steam Workshop

## Environment Variables

| Variable            | Description                                          | Required | Default |
| ------------------- | ---------------------------------------------------- | -------- | ------- |
| `STEAM_USER`        | Steam username                                       | Yes      | -       |
| `STEAM_PASS`        | Steam password                                       | Yes      | -       |
| `CONTENT_PATH`      | Path to addon files inside container                 | Yes      | -       |
| `TITLE`             | Workshop item title                                  | Yes      | -       |
| `DESCRIPTION`       | Workshop item description                            | Yes      | -       |
| `PUBLISHED_FILE_ID` | Existing workshop item ID (0 for new)                | No       | 0       |
| `VISIBILITY`        | Workshop visibility (0=public, 1=friends, 2=private) | No       | 0       |
| `STEAM_GUARD`       | Steam Guard code (if required)                       | No       | -       |
| `PREVIEW_FILE`      | Preview image path                                   | No       | -       |

## Visibility Options

-   `0`: Public (visible to everyone)
-   `1`: Friends Only (visible to Steam friends)
-   `2`: Private (visible only to you)

## Creating vs Updating Workshop Items

-   **New Item**: Set `PUBLISHED_FILE_ID` to `0`
-   **Update Existing**: Set `PUBLISHED_FILE_ID` to the workshop item's ID (found in the workshop URL)

## Example Addon Structure

This repository includes an example addon (`adn-test`) that demonstrates the proper file structure:

```lua
-- adn-test/lua/autorun/adn_test.lua
print("Hello from ADN test addon!")
```

## Manual Testing

You can test the Docker container locally:

```bash
# Build the image
docker build -t gmod-uploader .

# Run with your addon
docker run --rm \
  -e STEAM_USER="your_username" \
  -e STEAM_PASS="your_password" \
  -e CONTENT_PATH="/data/adn-test" \
  -e TITLE="ADN Test Addon" \
  -e DESCRIPTION="Test addon for automated deployment" \
  -e PUBLISHED_FILE_ID="0" \
  -v ./adn-test:/data/adn-test \
  gmod-uploader
```

## Security Considerations

-   **Never commit Steam credentials** to your repository
-   Use GitHub Secrets for sensitive information
-   Consider using Steam Guard for additional security
-   Keep your repository private if it contains sensitive addon code

## Troubleshooting

### Common Issues

1. **Steam Guard Required**: If you have Steam Guard enabled, you may need to provide the code via the `STEAM_GUARD` environment variable.

2. **Authentication Failed**: Verify your Steam credentials are correct and that your account has workshop publishing permissions.

3. **Invalid File Path**: Ensure the `CONTENT_PATH` matches the mounted volume path in the Docker command.

4. **Workshop Item Not Found**: When updating, make sure the `PUBLISHED_FILE_ID` is correct and you own the workshop item.

### Debug Mode

Add debug output to the entrypoint script for troubleshooting:

```bash
echo "Content path contents:"
ls -la "${CONTENT_PATH}"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with your own addon
5. Submit a pull request

## License

This project is provided as-is for educational and development purposes. Please respect Steam's terms of service and workshop guidelines when using this tool.
