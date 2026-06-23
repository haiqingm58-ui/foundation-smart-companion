#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="${APP_NAME:-foundation-smart-companion}"
DEPLOY_USER="${DEPLOY_USER:-deployer}"
REMOTE_BASE="${REMOTE_BASE:-/var/www/releases/${APP_NAME}}"
PUBLIC_LINK="${PUBLIC_LINK:-/var/www/html/${APP_NAME}}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this bootstrap script on the server as root." >&2
  exit 1
fi

if ! id "${DEPLOY_USER}" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "${DEPLOY_USER}"
fi

mkdir -p "${REMOTE_BASE}/releases" "${REMOTE_BASE}/shared" "$(dirname "${PUBLIC_LINK}")"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${REMOTE_BASE}"

if [[ ! -e "${PUBLIC_LINK}" ]]; then
  ln -s "${REMOTE_BASE}/current" "${PUBLIC_LINK}"
fi

chown -h "${DEPLOY_USER}:${DEPLOY_USER}" "${PUBLIC_LINK}" || true

install -d -m 700 -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" "/home/${DEPLOY_USER}/.ssh"
touch "/home/${DEPLOY_USER}/.ssh/authorized_keys"
chmod 600 "/home/${DEPLOY_USER}/.ssh/authorized_keys"
chown "${DEPLOY_USER}:${DEPLOY_USER}" "/home/${DEPLOY_USER}/.ssh/authorized_keys"

cat <<EOF
Server bootstrap complete.

Next:
1. Append your public key to /home/${DEPLOY_USER}/.ssh/authorized_keys
2. Install ops/nginx-foundation-smart-companion.conf into the active Nginx server block
3. Reload Nginx: nginx -t && systemctl reload nginx
4. Deploy from local machine:
   SSH_HOST=${DEPLOY_USER}@111.228.5.243 npm run deploy:jdcloud
EOF
