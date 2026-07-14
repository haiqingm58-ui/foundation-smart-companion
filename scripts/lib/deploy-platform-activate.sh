#!/usr/bin/env bash
set -Eeuo pipefail

: "${SOURCE_RELEASE:?SOURCE_RELEASE is required}"
: "${SOURCE_BASE:?SOURCE_BASE is required}"
: "${WEB_RELEASE:?WEB_RELEASE is required}"
: "${WEB_BASE:?WEB_BASE is required}"
: "${KEEP_RELEASES:?KEEP_RELEASES is required}"
: "${RELEASE_ID:?RELEASE_ID is required}"

PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
FOUNDATION_ENV_FILE="${FOUNDATION_ENV_FILE:-/etc/foundation-smart-companion.env}"

python3 -m venv "${SOURCE_RELEASE}/server/.venv"
"${SOURCE_RELEASE}/server/.venv/bin/pip" install --disable-pip-version-check -q --timeout 60 -i "${PIP_INDEX_URL}" -r "${SOURCE_RELEASE}/server/requirements.txt"

set -a
source "${FOUNDATION_ENV_FILE}"
set +a
cd "${SOURCE_RELEASE}"
"${SOURCE_RELEASE}/server/.venv/bin/python" -m server.manage migrate
"${SOURCE_RELEASE}/server/.venv/bin/python" -m server.manage import-question-bank "${SOURCE_RELEASE}/content/question-banks/soil-mechanics/manifest.json"
if [[ -f /var/lib/foundation-smart-companion/app.db ]]; then
  "${SOURCE_RELEASE}/server/.venv/bin/python" -m server.manage import-legacy /var/lib/foundation-smart-companion/app.db
fi
"${SOURCE_RELEASE}/server/.venv/bin/python" -c 'from server.app import app; assert app.title'

if [[ -d /opt/foundation-smart-companion && ! -L /opt/foundation-smart-companion ]]; then
  mv /opt/foundation-smart-companion "/opt/foundation-smart-companion-legacy-${RELEASE_ID}"
fi
ln -sfn "${SOURCE_RELEASE}" /opt/foundation-smart-companion.next
mv -Tf /opt/foundation-smart-companion.next /opt/foundation-smart-companion

ln -sfn "${WEB_RELEASE}" "${WEB_BASE}/current.next"
mv -Tf "${WEB_BASE}/current.next" "${WEB_BASE}/current"
ln -sfn "${WEB_BASE}/current" /var/www/foundation-smart-companion.next
mv -Tf /var/www/foundation-smart-companion.next /var/www/foundation-smart-companion

systemctl daemon-reload
systemctl restart foundation-smart-companion-api.service
nginx -t
systemctl reload nginx

find "${SOURCE_BASE}/releases" -mindepth 1 -maxdepth 1 -type d | sort -r | tail -n +$((KEEP_RELEASES + 1)) | xargs -r rm -rf
find "${WEB_BASE}/releases" -mindepth 1 -maxdepth 1 -type d | sort -r | tail -n +$((KEEP_RELEASES + 1)) | xargs -r rm -rf
