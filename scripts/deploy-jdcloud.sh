#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="${APP_NAME:-foundation-smart-companion}"
SSH_HOST="${SSH_HOST:-jdcloud}"
REMOTE_BASE="${REMOTE_BASE:-/var/www/releases/${APP_NAME}}"
PUBLIC_LINK="${PUBLIC_LINK:-/var/www/html/${APP_NAME}}"
PUBLIC_URL="${PUBLIC_URL:-http://111.228.5.243/${APP_NAME}/}"
KEEP_RELEASES="${KEEP_RELEASES:-5}"
SKIP_BUILD="${SKIP_BUILD:-0}"
MANAGE_PUBLIC_LINK="${MANAGE_PUBLIC_LINK:-0}"

if [[ "${SKIP_BUILD}" != "1" ]]; then
  npm run build
fi

if [[ ! -d dist ]]; then
  echo "dist/ does not exist. Run npm run build first." >&2
  exit 1
fi

GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo manual)"
RELEASE_ID="$(date +%Y%m%d%H%M%S)-${GIT_SHA}"
REMOTE_RELEASE="${REMOTE_BASE}/releases/${RELEASE_ID}"

echo "Deploying ${APP_NAME} ${RELEASE_ID} to ${SSH_HOST}"

ssh "${SSH_HOST}" "mkdir -p '${REMOTE_BASE}/releases' '${REMOTE_BASE}/shared'"
rsync -az --delete --checksum dist/ "${SSH_HOST}:${REMOTE_RELEASE}/"

ssh "${SSH_HOST}" "bash -s" <<EOF
set -Eeuo pipefail
REMOTE_BASE='${REMOTE_BASE}'
REMOTE_RELEASE='${REMOTE_RELEASE}'
PUBLIC_LINK='${PUBLIC_LINK}'
KEEP_RELEASES='${KEEP_RELEASES}'
MANAGE_PUBLIC_LINK='${MANAGE_PUBLIC_LINK}'

test -d "\${REMOTE_RELEASE}"
ln -sfn "\${REMOTE_RELEASE}" "\${REMOTE_BASE}/current.next"
mv -Tf "\${REMOTE_BASE}/current.next" "\${REMOTE_BASE}/current"

if [[ "\${MANAGE_PUBLIC_LINK}" == "1" && -n "\${PUBLIC_LINK}" ]]; then
  mkdir -p "\$(dirname "\${PUBLIC_LINK}")"
  ln -sfn "\${REMOTE_BASE}/current" "\${PUBLIC_LINK}.next"
  mv -Tf "\${PUBLIC_LINK}.next" "\${PUBLIC_LINK}"
fi

find "\${REMOTE_BASE}/releases" -mindepth 1 -maxdepth 1 -type d \
  | sort -r \
  | tail -n +\$((KEEP_RELEASES + 1)) \
  | xargs -r rm -rf
EOF

echo "Published release: ${REMOTE_RELEASE}"

if command -v curl >/dev/null 2>&1 && [[ -n "${PUBLIC_URL}" ]]; then
  echo "Checking ${PUBLIC_URL}"
  curl -fsSL "${PUBLIC_URL}" | grep -q "《基础工程》智慧学伴"
  echo "Health check passed."
fi
