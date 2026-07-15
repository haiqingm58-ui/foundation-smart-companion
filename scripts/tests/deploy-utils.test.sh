#!/usr/bin/env bash
set -Eeuo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/deploy-utils.sh"

attempts=0
curl() {
  attempts=$((attempts + 1))
  [[ "${attempts}" -ge 3 ]]
}

wait_for_http "http://example.test/health" 4 0
[[ "${attempts}" -eq 3 ]]

attempts=0
if wait_for_http "http://example.test/health" 2 0 2>/dev/null; then
  echo "expected wait_for_http to fail after two attempts" >&2
  exit 1
fi
[[ "${attempts}" -eq 2 ]]

curl() {
  local argument
  for argument in "$@"; do
    if [[ "${argument}" == -*L* ]]; then
      printf '<title>《基础工程》智慧学伴</title>'
      return 0
    fi
  done
  printf '<html>redirect</html>'
}

verify_page_contains "http://example.test/login" "《基础工程》智慧学伴"

scripts_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
deploy_script="${scripts_dir}/deploy-platform-jdcloud.sh"
activation_script="${scripts_dir}/lib/deploy-platform-activate.sh"
rg -q 'source "\\?\$\{SOURCE_RELEASE\}/scripts/lib/deploy-platform-activate\.sh"' "${deploy_script}"
migration_line=$(rg -n 'server\.manage migrate' "${activation_script}" | head -n 1 | cut -d: -f1)
import_line=$(rg -n 'server\.manage import-question-bank' "${activation_script}" | head -n 1 | cut -d: -f1)
font_install_line=$(rg -n 'fonts-wqy-zenhei' "${activation_script}" | head -n 1 | cut -d: -f1)
font_preflight_line=$(rg -n 'TTFont' "${activation_script}" | head -n 1 | cut -d: -f1)
source_switch_line=$(rg -n 'mv -Tf /opt/foundation-smart-companion\.next /opt/foundation-smart-companion' "${activation_script}" | head -n 1 | cut -d: -f1)
restart_line=$(rg -n 'systemctl restart foundation-smart-companion-api\.service' "${activation_script}" | head -n 1 | cut -d: -f1)
nginx_reload_line=$(rg -n 'systemctl reload nginx' "${activation_script}" | head -n 1 | cut -d: -f1)
[[ -n "${font_install_line}" && -n "${font_preflight_line}" && -n "${migration_line}" && -n "${import_line}" && -n "${source_switch_line}" && -n "${restart_line}" && -n "${nginx_reload_line}" ]]
[[ "${font_install_line}" -lt "${font_preflight_line}" && "${font_preflight_line}" -lt "${migration_line}" ]]
[[ "${migration_line}" -lt "${import_line}" ]]
pointer_count=0
while IFS=: read -r pointer_line _; do
  pointer_count=$((pointer_count + 1))
  [[ "${import_line}" -lt "${pointer_line}" ]]
done < <(rg -n 'ln -sfn .*\.next|mv -Tf .*\.next' "${activation_script}")
[[ "${pointer_count}" -eq 6 ]]
[[ "${import_line}" -lt "${restart_line}" && "${import_line}" -lt "${nginx_reload_line}" ]]

activation_root="$(mktemp -d)"
actions_file="${activation_root}/actions.log"
source_release="${activation_root}/source-release"
web_release="${activation_root}/web-release"
source_base="${activation_root}/source-base"
web_base="${activation_root}/web-base"
stub_bin="${activation_root}/bin"
env_file="${activation_root}/foundation.env"
font_path="${activation_root}/fonts/wqy-zenhei.ttc"
mkdir -p "${source_release}/server/.venv/bin" "${source_release}/content/question-banks/soil-mechanics" "${source_release}/scripts/lib" "${web_release}" "${source_base}/releases" "${web_base}/releases" "${stub_bin}"
cp "${activation_script}" "${source_release}/scripts/lib/deploy-platform-activate.sh"
printf 'FOUNDATION_DATABASE_URL=sqlite:///%s/test.db\n' "${activation_root}" > "${env_file}"

cat > "${source_release}/server/.venv/bin/python" <<'EOF'
#!/usr/bin/env bash
printf 'python %s\n' "$*" >> "${ACTIVATION_ACTIONS_FILE}"
if [[ "$*" == "-m server.manage import-question-bank "* ]]; then
  exit 47
fi
exit 0
EOF
cat > "${source_release}/server/.venv/bin/pip" <<'EOF'
#!/usr/bin/env bash
printf 'pip %s\n' "$*" >> "${ACTIVATION_ACTIONS_FILE}"
EOF
cat > "${stub_bin}/python3" <<'EOF'
#!/usr/bin/env bash
printf 'python3 %s\n' "$*" >> "${ACTIVATION_ACTIONS_FILE}"
EOF
cat > "${stub_bin}/apt-get" <<'EOF'
#!/usr/bin/env bash
printf 'apt-get %s\n' "$*" >> "${ACTIVATION_ACTIONS_FILE}"
if [[ "$*" == *" install "* || "$*" == install\ * ]]; then
  mkdir -p "$(dirname "${FOUNDATION_PDF_FONT_PATH}")"
  printf 'synthetic-font' > "${FOUNDATION_PDF_FONT_PATH}"
fi
EOF
for command in ln mv systemctl nginx find; do
  cat > "${stub_bin}/${command}" <<EOF
#!/usr/bin/env bash
printf '${command} %s\\n' "\$*" >> "\${ACTIVATION_ACTIONS_FILE}"
EOF
  chmod +x "${stub_bin}/${command}"
done
chmod +x "${source_release}/server/.venv/bin/python" "${source_release}/server/.venv/bin/pip" "${stub_bin}/python3" "${stub_bin}/apt-get"

if PATH="${stub_bin}:${PATH}" ACTIVATION_ACTIONS_FILE="${actions_file}" FOUNDATION_PDF_FONT_PATH="${font_path}" FOUNDATION_ENV_FILE="${env_file}" SOURCE_RELEASE="${source_release}" SOURCE_BASE="${source_base}" WEB_RELEASE="${web_release}" WEB_BASE="${web_base}" KEEP_RELEASES=5 RELEASE_ID=test-release bash "${source_release}/scripts/lib/deploy-platform-activate.sh"; then
  echo "expected import failure to stop production activation script" >&2
  exit 1
fi
rg -q --fixed-strings "apt-get update" "${actions_file}"
rg -q --fixed-strings "apt-get install -y --no-install-recommends fonts-wqy-zenhei" "${actions_file}"
rg -q --fixed-strings "python -c from reportlab.pdfbase.ttfonts import TTFont" "${actions_file}"
rg -q --fixed-strings "python -m server.manage migrate" "${actions_file}"
rg -q --fixed-strings "python -m server.manage import-question-bank ${source_release}/content/question-banks/soil-mechanics/manifest.json" "${actions_file}"
[[ "$(wc -l < "${actions_file}")" -eq 7 ]]
if rg -q '^(ln|mv|systemctl|nginx|find) ' "${actions_file}"; then
  echo "activation continued after import failure" >&2
  cat "${actions_file}" >&2
  exit 1
fi
rm -rf "${activation_root}"

echo "deploy-utils tests passed"
