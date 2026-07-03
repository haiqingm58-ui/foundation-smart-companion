#!/usr/bin/env bash
set -Eeuo pipefail

SSH_HOST="${SSH_HOST:-jdcloud}"
APP_NAME="foundation-smart-companion"
SOURCE_BASE="/opt/${APP_NAME}-releases"
WEB_BASE="/var/www/releases/${APP_NAME}"
KEEP_RELEASES="${KEEP_RELEASES:-5}"
GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo manual)"
RELEASE_ID="$(date +%Y%m%d%H%M%S)-${GIT_SHA}"
SOURCE_RELEASE="${SOURCE_BASE}/releases/${RELEASE_ID}"
WEB_RELEASE="${WEB_BASE}/releases/${RELEASE_ID}"

npm run build
npm test
server/.venv/bin/pytest server/tests -q

ssh "${SSH_HOST}" "mkdir -p '${SOURCE_RELEASE}' '${WEB_RELEASE}' '${SOURCE_BASE}/releases' '${WEB_BASE}/releases'"
rsync -az --delete \
  --exclude '.git' --exclude 'node_modules' --exclude 'dist' --exclude 'server/.venv' \
  ./ "${SSH_HOST}:${SOURCE_RELEASE}/"
rsync -az --delete dist/ "${SSH_HOST}:${WEB_RELEASE}/"

ssh "${SSH_HOST}" "bash -s" <<EOF
set -Eeuo pipefail
SOURCE_RELEASE='${SOURCE_RELEASE}'
SOURCE_BASE='${SOURCE_BASE}'
WEB_RELEASE='${WEB_RELEASE}'
WEB_BASE='${WEB_BASE}'
KEEP_RELEASES='${KEEP_RELEASES}'

python3 -m venv "\${SOURCE_RELEASE}/server/.venv"
"\${SOURCE_RELEASE}/server/.venv/bin/pip" install --disable-pip-version-check -q -r "\${SOURCE_RELEASE}/server/requirements.txt"

set -a
source /etc/foundation-smart-companion.env
set +a
cd "\${SOURCE_RELEASE}"
"\${SOURCE_RELEASE}/server/.venv/bin/python" -m server.manage migrate
if [[ -f /var/lib/foundation-smart-companion/app.db ]]; then
  "\${SOURCE_RELEASE}/server/.venv/bin/python" -m server.manage import-legacy /var/lib/foundation-smart-companion/app.db
fi
"\${SOURCE_RELEASE}/server/.venv/bin/python" -c 'from server.app import app; assert app.title'

if [[ -d /opt/foundation-smart-companion && ! -L /opt/foundation-smart-companion ]]; then
  mv /opt/foundation-smart-companion "/opt/foundation-smart-companion-legacy-${RELEASE_ID}"
fi
ln -sfn "\${SOURCE_RELEASE}" /opt/foundation-smart-companion.next
mv -Tf /opt/foundation-smart-companion.next /opt/foundation-smart-companion

ln -sfn "\${WEB_RELEASE}" "\${WEB_BASE}/current.next"
mv -Tf "\${WEB_BASE}/current.next" "\${WEB_BASE}/current"
ln -sfn "\${WEB_BASE}/current" /var/www/foundation-smart-companion.next
mv -Tf /var/www/foundation-smart-companion.next /var/www/foundation-smart-companion

systemctl daemon-reload
systemctl restart foundation-smart-companion-api.service
nginx -t
systemctl reload nginx

find "\${SOURCE_BASE}/releases" -mindepth 1 -maxdepth 1 -type d | sort -r | tail -n +\$((KEEP_RELEASES + 1)) | xargs -r rm -rf
find "\${WEB_BASE}/releases" -mindepth 1 -maxdepth 1 -type d | sort -r | tail -n +\$((KEEP_RELEASES + 1)) | xargs -r rm -rf
EOF

curl -fsS "http://111.228.5.243/${APP_NAME}/api/health" >/dev/null
curl -fsS "http://111.228.5.243/${APP_NAME}/login" | grep -q "《基础工程》智慧学伴"
echo "Deployment completed: ${RELEASE_ID}"
