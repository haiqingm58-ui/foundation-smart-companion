# Operations Runbook

This folder contains deployment and quality-gate helpers for the Foundation Smart Companion.

## JDCloud zero-downtime deploy

Recommended layout:

```text
/var/www/releases/foundation-smart-companion/
  releases/
    20260623193000-abcdef/
    20260623201000-123456/
  current -> releases/20260623201000-123456

/var/www/html/foundation-smart-companion -> /var/www/releases/foundation-smart-companion/current
```

One-time server setup as root:

```bash
APP_NAME=foundation-smart-companion \
DEPLOY_USER=deployer \
REMOTE_BASE=/var/www/releases/foundation-smart-companion \
PUBLIC_LINK=/var/www/html/foundation-smart-companion \
bash ops/jdcloud-bootstrap.sh
```

Then add the deployer's SSH public key to:

```text
/home/deployer/.ssh/authorized_keys
```

Install `ops/nginx-foundation-smart-companion.conf` inside the active Nginx server block and reload:

```bash
nginx -t && systemctl reload nginx
```

Local release command:

```bash
SSH_HOST=deployer@111.228.5.243 npm run deploy:jdcloud
```

The deploy script uploads `dist/` into a timestamped release directory, switches `current` atomically, and prunes old releases.

By default, each deploy only changes the `current` symlink under `REMOTE_BASE`. The public link under `/var/www/html` is created during bootstrap. Only set `MANAGE_PUBLIC_LINK=1` when the deploy user intentionally has write access to the public web root.

## GitHub Pages Actions

The current OAuth token cannot push files under `.github/workflows/` because it lacks the `workflow` scope. After enabling workflow permissions:

1. Move `ops/github-pages-actions.yml` to `.github/workflows/deploy-pages.yml`.
2. In GitHub repository settings, set Pages source to GitHub Actions.
3. Push to `main`.

The workflow builds with Vite, runs the prerender postbuild step, uploads `dist/`, and deploys Pages via `actions/deploy-pages`.

## Lighthouse CI

Run locally after a build:

```bash
npm run build
npm run perf:lhci
```

The current thresholds are intentionally progressive:

- SEO fails below 90.
- CLS fails above 0.1.
- Performance, accessibility, best practices, and LCP warn first.

After the hero image is further optimized, raise the performance assertion toward 90 and change it from `warn` to `error`.
