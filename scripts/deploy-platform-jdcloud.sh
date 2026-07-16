#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/deploy-utils.sh"

SSH_HOST="${SSH_HOST:-jdcloud}"
SSH_OPTIONS=(-o ServerAliveInterval=10 -o ServerAliveCountMax=12)
RSYNC_RSH="ssh -o ServerAliveInterval=10 -o ServerAliveCountMax=12"
APP_NAME="foundation-smart-companion"
SOURCE_BASE="/opt/${APP_NAME}-releases"
WEB_BASE="/var/www/releases/${APP_NAME}"
KEEP_RELEASES="${KEEP_RELEASES:-5}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo manual)"
RELEASE_ID="$(date +%Y%m%d%H%M%S)-${GIT_SHA}"
SOURCE_RELEASE="${SOURCE_BASE}/releases/${RELEASE_ID}"
WEB_RELEASE="${WEB_BASE}/releases/${RELEASE_ID}"

npm run check
npm run test:e2e

ssh "${SSH_OPTIONS[@]}" "${SSH_HOST}" "mkdir -p '${SOURCE_RELEASE}' '${WEB_RELEASE}' '${SOURCE_BASE}/releases' '${WEB_BASE}/releases'"
rsync -az --delete -e "${RSYNC_RSH}" \
  --exclude '.git' --exclude 'node_modules' --exclude 'dist' --exclude 'server/.venv' \
  ./ "${SSH_HOST}:${SOURCE_RELEASE}/"
rsync -az --delete -e "${RSYNC_RSH}" dist/ "${SSH_HOST}:${WEB_RELEASE}/"

ssh "${SSH_OPTIONS[@]}" "${SSH_HOST}" "bash -s" <<EOF
set -Eeuo pipefail
export SOURCE_RELEASE='${SOURCE_RELEASE}'
export SOURCE_BASE='${SOURCE_BASE}'
export WEB_RELEASE='${WEB_RELEASE}'
export WEB_BASE='${WEB_BASE}'
export KEEP_RELEASES='${KEEP_RELEASES}'
export PIP_INDEX_URL='${PIP_INDEX_URL}'
export RELEASE_ID='${RELEASE_ID}'
source "\${SOURCE_RELEASE}/scripts/lib/deploy-platform-activate.sh"
EOF

wait_for_http "http://111.228.5.243/${APP_NAME}/api/health" 30 1
verify_page_contains "http://111.228.5.243/${APP_NAME}/login" "《基础工程》智慧学伴"
echo "Deployment completed: ${RELEASE_ID}"
