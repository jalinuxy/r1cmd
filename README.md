# r1 — Arvan Storage CLI

<p align="center">
  <strong>ابزار ساده برای مدیریت فایل‌ها در فضای ابری آروان</strong><br>
  <strong>A simple, friendly CLI for ArvanCloud Object Storage</strong>
</p>

<p align="center">
  <a href="https://www.arvancloud.ir/fa/products/cloud-storage">ArvanCloud Object Storage</a> ·
  <a href="https://jalinuxy.ir/r1cmd">One-line install</a> ·
  <a href="https://github.com/jalinuxy/r1cmd">GitHub</a>
</p>

---

## Table of contents

- [What is r1?](#what-is-r1)
- [Quick start](#quick-start)
- [Installation](#installation)
- [First-time setup](#first-time-setup)
- [Interactive menu](#interactive-menu)
- [CLI reference](#cli-reference)
- [Docker](#docker)
- [Python library](#python-library)
- [Configuration](#configuration)
- [Environment variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Why not aws / s3cmd?](#why-not-aws--s3cmd)
- [License](#license)

---

## What is r1?

**r1** is a command-line tool and Python library for [ArvanCloud Object Storage](https://www.arvancloud.ir/fa/products/cloud-storage).

You do **not** need to know S3, endpoints, or AWS concepts. Just your **Access Key** and **Secret Key** from the Arvan panel — r1 handles the rest.

| Feature | Description |
|---------|-------------|
| Interactive TUI | Guided menu for upload, download, browse, delete, share links |
| Simple CLI | One-liner commands for scripts and daily use |
| Python library | Use `ArvanStorage` in your own apps |
| Zero endpoint config | Arvan S3 endpoint is built in |
| Docker image | Run in containers with mounted config and data |

---

## Quick start

```bash
# Install (one command)
curl -fsSL https://jalinuxy.ir/r1cmd | sh

# Save credentials (30 seconds)
r1 setup

# Open the menu
r1
```

**شروع سریع (فارسی):**

```bash
# نصب با یک دستور
curl -fsSL https://jalinuxy.ir/r1cmd | sh

# ذخیره Access Key و Secret Key
r1 setup

# باز کردن منوی تعاملی
r1
```

---

## Installation

### Option 1 — One-line install (recommended)

Works on Linux and macOS with Python 3.9+:

```bash
curl -fsSL https://jalinuxy.ir/r1cmd | sh
```

The script installs `r1cmd` from PyPI (or GitHub if PyPI is unavailable) into `~/.local/bin`.  
If `r1` is not found afterward, add this to your shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Pin a version:

```bash
curl -fsSL https://jalinuxy.ir/r1cmd | R1CMD_VERSION=0.2.0 sh
```

### Option 2 — pip

```bash
pip install r1cmd
# or from source
pip install git+https://github.com/jalinuxy/r1cmd.git
```

### Option 3 — Clone and run install.sh

For contributors or offline builds:

```bash
git clone https://github.com/jalinuxy/r1cmd.git
cd r1cmd
./install.sh          # creates .venv/ and installs locally
./install.sh --dev    # includes pytest and moto
./install.sh --user   # install to ~/.local/bin without venv
```

### Option 4 — Docker

```bash
docker pull jalinuxy/r1cmd:latest
# or build locally:
docker build -t jalinuxy/r1cmd .
```

See [Docker](#docker) for usage examples.

### Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.9 or newer |
| OS | Linux, macOS, Windows (WSL) |
| Network | Access to Arvan Object Storage API |

---

## First-time setup

Run the setup wizard once:

```bash
r1 setup
```

You will enter:

1. **Access Key** — from Arvan panel → Object Storage → Access Keys
2. **Secret Key**
3. **Default storage space** — picked from your account

Credentials are saved to:

```
~/.config/r1cmd/config.json
```

File permissions are set to `600` (readable only by you).

**تنظیم اولیه:** کلیدها را از پنل آروان → فضای ابری → Access Keys بگیرید و با `r1 setup` ذخیره کنید.

---

## Interactive menu

```bash
r1
```

Opens a guided terminal UI:

| Action | Description |
|--------|-------------|
| Upload a file | Send a local file to your storage space |
| Download a file | Save a remote file to your computer |
| Browse my files | List folders and files |
| Delete a file | Remove a file from storage |
| Get a shareable link | Temporary presigned download URL |
| Switch storage space | Change the active space |
| Settings | View or update saved credentials |

---

## CLI reference

### General

```bash
r1                  # interactive menu
r1 --help           # show all commands
r1 setup            # save credentials
r1 spaces           # list storage spaces
```

### Upload

```bash
r1 upload photo.jpg
r1 upload photo.jpg albums/summer/photo.jpg
r1 upload backup.zip --space my-backups
```

### Download

```bash
r1 download reports/2024.pdf
r1 download reports/2024.pdf ./downloads/report.pdf
r1 download data/export.csv --space archives
```

### Browse

```bash
r1 browse
r1 browse photos
r1 browse photos/2024 --space media
```

### Delete

```bash
r1 delete old/backup.zip
r1 delete temp/file.log --space logs
```

### Share link

```bash
r1 link videos/clip.mp4
r1 link docs/guide.pdf --hours 6
r1 link public/image.png --hours 48 --space cdn
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (credentials, network, file not found, etc.) |
| `130` | Interrupted (Ctrl+C) |

---

## Docker

### Pull image

```bash
docker pull jalinuxy/r1cmd:latest
```

### Interactive menu

```bash
docker run -it --rm \
  -v ~/.config/r1cmd:/config/r1cmd \
  -v "$(pwd)":/data \
  jalinuxy/r1cmd
```

### One-time setup in Docker

```bash
docker run -it --rm \
  -v ~/.config/r1cmd:/config/r1cmd \
  jalinuxy/r1cmd setup
```

### Upload / download

```bash
docker run --rm \
  -v ~/.config/r1cmd:/config/r1cmd \
  -v "$(pwd)":/data \
  jalinuxy/r1cmd upload photo.jpg

docker run --rm \
  -v ~/.config/r1cmd:/config/r1cmd \
  -v "$(pwd)":/data \
  jalinuxy/r1cmd download reports/2024.pdf
```

### Environment variables (no setup wizard)

```bash
docker run --rm \
  -e ARVAN_ACCESS_KEY_ID=your-key \
  -e ARVAN_SECRET_ACCESS_KEY=your-secret \
  -e ARVAN_SPACE=my-space \
  -v "$(pwd)":/data \
  jalinuxy/r1cmd browse
```

### docker compose

```bash
# Setup
docker compose run --rm r1 setup

# Upload from current directory
docker compose run --rm r1 upload photo.jpg

# Interactive menu
docker compose run --rm r1
```

Override paths:

```bash
R1_CONFIG_DIR=~/.config/r1cmd R1_DATA_DIR=./files docker compose run --rm r1 browse
```

### Build and push your own image

```bash
docker build -t jalinuxy/r1cmd:latest .
docker push jalinuxy/r1cmd:latest
```

---

## Python library

Install the package, then import `ArvanStorage`:

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

### Direct credentials

```python
storage = ArvanStorage.from_credentials(
    access_key="your-key",
    secret_key="your-secret",
    space="my-space",
)

storage.upload("backup.zip", "daily/backup.zip")
```

### From environment variables

```python
from r1cmd import ArvanStorage

storage = ArvanStorage.from_env()   # reads ARVAN_* or AWS_* vars
storage.upload("data.csv")
```

### Advanced API

Lower-level S3 operations are also available:

```python
storage.list_objects(prefix="logs/")
storage.iter_objects(prefix="backups/")
storage.head_object("file.zip")
storage.delete_objects(["a.txt", "b.txt"])
storage.copy_object("src.txt", "dst.txt")
storage.generate_presigned_url("file.pdf", expires_in=7200)
storage.list_buckets()
storage.create_bucket("new-space")
```

### Library exceptions

```python
from r1cmd import ArvanStorageError

try:
    storage.download("missing.txt")
except ArvanStorageError as exc:
    print(exc)  # user-friendly message
```

---

## Configuration

### Config file

| Path | Purpose |
|------|---------|
| `~/.config/r1cmd/config.json` | Saved Access Key, Secret Key, default space |
| `$XDG_CONFIG_HOME/r1cmd/config.json` | Same, when `XDG_CONFIG_HOME` is set |

Example `config.json`:

```json
{
  "access_key": "your-access-key",
  "secret_key": "your-secret-key",
  "default_space": "my-space"
}
```

### Built-in endpoint

r1 uses the Arvan S3-compatible endpoint by default:

```
https://s3.ir-thr-at1.arvanstorage.ir
```

You rarely need to change this. Override with `ARVAN_ENDPOINT_URL` if required.

---

## Environment variables

For scripts, CI, and Docker — skip `r1 setup`:

| Variable | Required | Description |
|----------|----------|-------------|
| `ARVAN_ACCESS_KEY_ID` | Yes* | Access Key from Arvan panel |
| `ARVAN_SECRET_ACCESS_KEY` | Yes* | Secret Key |
| `ARVAN_SPACE` | No | Default storage space (bucket) |
| `ARVAN_ENDPOINT_URL` | No | Override S3 endpoint |
| `ARVAN_REGION` | No | Region name (default: `default`) |

\* Not required if `~/.config/r1cmd/config.json` exists.

**AWS-compatible aliases** (also supported): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL`, `AWS_BUCKET`.

Example `.env` file:

```env
ARVAN_ACCESS_KEY_ID=your-key
ARVAN_SECRET_ACCESS_KEY=your-secret
ARVAN_SPACE=my-space
```

```bash
export $(grep -v '^#' .env | xargs)
r1 browse
```

---

## Troubleshooting

### `r1: command not found` after curl install

Add `~/.local/bin` to your PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### `No saved credentials found`

Run `r1 setup` or set `ARVAN_ACCESS_KEY_ID` and `ARVAN_SECRET_ACCESS_KEY`.

### `Your Access Key looks wrong`

Double-check keys in Arvan panel → Object Storage → Access Keys. Re-run `r1 setup`.

### `No storage space selected`

Run `r1 setup` and pick a default space, or pass `--space NAME` / set `ARVAN_SPACE`.

### Python not found

Install Python 3.9+:

```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip python3-venv

# macOS
brew install python@3.12
```

### Docker: permission denied on config

Ensure the mounted config directory is writable:

```bash
mkdir -p ~/.config/r1cmd
chmod 700 ~/.config/r1cmd
```

---

## Development

```bash
git clone https://github.com/jalinuxy/r1cmd.git
cd r1cmd
./install.sh --dev
source .venv/bin/activate
pytest
```

### Project layout

```
r1cmd/
├── src/r1cmd/
│   ├── cli.py        # CLI entry point (r1 command)
│   ├── core.py       # ArvanStorage client
│   ├── config.py     # ~/.config/r1cmd handling
│   ├── tui.py        # Interactive menu
│   └── constants.py  # Endpoint and app name
├── install.sh        # Local + remote installer
├── Dockerfile
├── docker-compose.yml
└── deploy/           # nginx config for jalinuxy.ir/r1cmd
```

### Publish install script to jalinuxy.ir

See [`deploy/README.md`](deploy/README.md).

### Release to PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```

---

## Why not aws / s3cmd?

| aws / s3cmd | r1 |
|-------------|-----|
| Needs endpoint URLs, profiles, S3 concepts | Fixed Arvan endpoint — only keys needed |
| CLI-only (or separate SDK) | Interactive menu **and** Python library |
| Built for AWS power users | Built for Arvan users who just want to move files |
| Complex `~/.aws/credentials` setup | `r1 setup` wizard in 30 seconds |

---

## License

MIT — see [LICENSE](LICENSE) (if present) or project metadata in `pyproject.toml`.

---

<p align="center">
  Made for <a href="https://www.arvancloud.ir">ArvanCloud</a> users ·
  <a href="https://github.com/jalinuxy/r1cmd/issues">Report an issue</a>
</p>
