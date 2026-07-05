# Deploy install script to jalinuxy.ir

The one-liner users run:

```bash
curl -fsSL https://jalinuxy.ir/r1cmd | sh
```

## Steps

1. Upload `install.sh` to the server:

```bash
scp install.sh user@jalinuxy.ir:/var/www/jalinuxy/r1cmd/install.sh
ssh user@jalinuxy.ir 'chmod 644 /var/www/jalinuxy/r1cmd/install.sh'
```

2. Add the nginx snippet from [`nginx-r1cmd.conf`](nginx-r1cmd.conf) to your site config.

3. Test and reload:

```bash
curl -fsSL https://jalinuxy.ir/r1cmd | head -5
sudo nginx -t && sudo systemctl reload nginx
```

## Updating

After each release, re-upload `install.sh` (if changed) and publish the package to PyPI so remote installs resolve `r1cmd` quickly:

```bash
pip install build twine
python -m build
twine upload dist/*
```

## Pin a version

```bash
curl -fsSL https://jalinuxy.ir/r1cmd | R1CMD_VERSION=0.2.0 sh
```
