# r1 — Arvan Storage CLI

A **simple, friendly** tool for [ArvanCloud Object Storage](https://www.arvancloud.ir/en/products/cloud-storage).

No S3 knowledge required. No endpoint configuration. Just your **Access Key** and **Secret Key** from the Arvan panel.

Install the **r1cmd** package, then run the **r1** command.

## Install

```bash
pip install .
```

## First-time setup (30 seconds)

```bash
r1 setup
```

You will be asked for:

1. **Access Key**
2. **Secret Key**
3. **Default storage space** (picked from your account)

Credentials are saved to `~/.config/r1cmd/config.json`.

## Interactive menu

```bash
r1
```

Opens a guided terminal UI:

- Upload a file
- Download a file
- Browse my files
- Delete a file
- Get a shareable link
- Switch storage space
- Settings

## Quick commands

```bash
r1 upload photo.jpg
r1 upload photo.jpg albums/summer/photo.jpg
r1 download reports/2024.pdf
r1 browse
r1 browse photos
r1 link videos/clip.mp4 --hours 6
r1 spaces
```

## Use as a Python library

```python
from r1cmd import ArvanStorage

# Uses saved credentials from `r1 setup`
storage = ArvanStorage.connect()

storage.upload("photo.jpg")
storage.download("reports/2024.pdf", "report.pdf")

for file in storage.browse(folder="photos"):
    print(file.name, file.size)

link = storage.share_link("videos/clip.mp4", expires_in=3600)
```

Or pass keys directly (endpoint is built-in):

```python
storage = ArvanStorage.from_credentials(
    access_key="your-key",
    secret_key="your-secret",
    space="my-space",
)

storage.upload("backup.zip", "daily/backup.zip")
```

## Why not aws / s3cmd?

| aws / s3cmd | r1 |
|---|---|
| Needs endpoint URLs, profiles, S3 concepts | Fixed Arvan endpoint — only keys needed |
| CLI-only (or separate SDK) | Interactive menu **and** Python library |
| Built for AWS power users | Built for Arvan users who just want to move files |

## Environment variables (optional)

For scripts and CI, you can skip the setup wizard:

```env
ARVAN_ACCESS_KEY_ID=your-key
ARVAN_SECRET_ACCESS_KEY=your-secret
ARVAN_SPACE=my-space
```

`ARVAN_ENDPOINT_URL` is optional — the Arvan endpoint is included by default.
