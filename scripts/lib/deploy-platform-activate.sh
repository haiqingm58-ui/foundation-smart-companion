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
FOUNDATION_PDF_FONT_PATH="${FOUNDATION_PDF_FONT_PATH:-/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc}"
FOUNDATION_PDF_FONT_SUBFONT_INDEX="${FOUNDATION_PDF_FONT_SUBFONT_INDEX:-0}"
ACTIVATION_HEALTH_URL="${ACTIVATION_HEALTH_URL:-http://127.0.0.1:8000/api/health}"
SOURCE_POINTER="/opt/foundation-smart-companion"
WEB_POINTER="${WEB_BASE}/current"
PUBLIC_WEB_POINTER="/var/www/foundation-smart-companion"
PREVIOUS_SOURCE=""
PREVIOUS_WEB=""
LEGACY_SOURCE=""
SWITCH_STARTED=0

source "${SOURCE_RELEASE}/scripts/lib/deploy-utils.sh"

restore_pointer() {
  local pointer="$1"
  local previous="$2"
  if [[ -n "${previous}" ]]; then
    ln -sfn "${previous}" "${pointer}.rollback"
    mv -Tf "${pointer}.rollback" "${pointer}"
  else
    rm -f "${pointer}"
  fi
}

rollback_activation() {
  local status=$?
  trap - ERR
  if ((SWITCH_STARTED == 1)); then
    echo "Activation failed; restoring previous release pointers." >&2
    set +e
    if [[ -n "${LEGACY_SOURCE}" ]]; then
      rm -f "${SOURCE_POINTER}"
      mv -Tf "${LEGACY_SOURCE}" "${SOURCE_POINTER}"
    else
      restore_pointer "${SOURCE_POINTER}" "${PREVIOUS_SOURCE}"
    fi
    restore_pointer "${WEB_POINTER}" "${PREVIOUS_WEB}"
    if [[ -n "${PREVIOUS_WEB}" ]]; then
      restore_pointer "${PUBLIC_WEB_POINTER}" "${WEB_POINTER}"
    else
      rm -f "${PUBLIC_WEB_POINTER}"
    fi
    systemctl daemon-reload
    systemctl restart foundation-smart-companion-api.service
    nginx -t && systemctl reload nginx
  fi
  exit "${status}"
}

trap rollback_activation ERR

if [[ ! -r "${FOUNDATION_PDF_FONT_PATH}" ]]; then
  apt-get update
  apt-get install -y --no-install-recommends fonts-wqy-zenhei
fi
if [[ ! -r "${FOUNDATION_PDF_FONT_PATH}" ]]; then
  echo "PDF Chinese font is unavailable after provisioning: ${FOUNDATION_PDF_FONT_PATH}" >&2
  exit 1
fi
export FOUNDATION_PDF_FONT_PATH FOUNDATION_PDF_FONT_SUBFONT_INDEX

python3 -m venv "${SOURCE_RELEASE}/server/.venv"
"${SOURCE_RELEASE}/server/.venv/bin/pip" install --disable-pip-version-check -q --timeout 60 -i "${PIP_INDEX_URL}" -r "${SOURCE_RELEASE}/server/requirements.txt"
"${SOURCE_RELEASE}/server/.venv/bin/python" -c 'from reportlab.pdfbase.ttfonts import TTFont; import os; font = TTFont("FoundationPdfPreflight", os.environ["FOUNDATION_PDF_FONT_PATH"], subfontIndex=int(os.environ["FOUNDATION_PDF_FONT_SUBFONT_INDEX"])); assert all(ord(char) in font.face.charToGlyph for char in "土力学试卷")'

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

if [[ -d "${SOURCE_POINTER}" && ! -L "${SOURCE_POINTER}" ]]; then
  LEGACY_SOURCE="/opt/foundation-smart-companion-legacy-${RELEASE_ID}"
  mv "${SOURCE_POINTER}" "${LEGACY_SOURCE}"
else
  PREVIOUS_SOURCE="$(readlink -f "${SOURCE_POINTER}" 2>/dev/null || true)"
fi
PREVIOUS_WEB="$(readlink -f "${WEB_POINTER}" 2>/dev/null || true)"

nginx -t
SWITCH_STARTED=1
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
wait_for_http "${ACTIVATION_HEALTH_URL}" 30 1

SWITCH_STARTED=0
trap - ERR

find "${SOURCE_BASE}/releases" -mindepth 1 -maxdepth 1 -type d | sort -r | tail -n +$((KEEP_RELEASES + 1)) | xargs -r rm -rf
find "${WEB_BASE}/releases" -mindepth 1 -maxdepth 1 -type d | sort -r | tail -n +$((KEEP_RELEASES + 1)) | xargs -r rm -rf
