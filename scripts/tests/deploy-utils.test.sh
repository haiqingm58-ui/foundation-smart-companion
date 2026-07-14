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

deploy_script="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/deploy-platform-jdcloud.sh"
migration_line=$(rg -n 'server\.manage migrate' "${deploy_script}" | head -n 1 | cut -d: -f1)
import_line=$(rg -n 'server\.manage import-question-bank' "${deploy_script}" | head -n 1 | cut -d: -f1)
source_switch_line=$(rg -n 'mv -Tf /opt/foundation-smart-companion\.next /opt/foundation-smart-companion' "${deploy_script}" | head -n 1 | cut -d: -f1)
restart_line=$(rg -n 'systemctl restart foundation-smart-companion-api\.service' "${deploy_script}" | head -n 1 | cut -d: -f1)
nginx_reload_line=$(rg -n 'systemctl reload nginx' "${deploy_script}" | head -n 1 | cut -d: -f1)
[[ -n "${migration_line}" && -n "${import_line}" && -n "${source_switch_line}" && -n "${restart_line}" && -n "${nginx_reload_line}" ]]
[[ "${migration_line}" -lt "${import_line}" ]]
pointer_count=0
while IFS=: read -r pointer_line _; do
  pointer_count=$((pointer_count + 1))
  [[ "${import_line}" -lt "${pointer_line}" ]]
done < <(rg -n 'ln -sfn .*\.next|mv -Tf .*\.next' "${deploy_script}")
[[ "${pointer_count}" -eq 6 ]]
[[ "${import_line}" -lt "${restart_line}" && "${import_line}" -lt "${nginx_reload_line}" ]]

actions_file="$(mktemp)"
record_action() { printf '%s\n' "$1" >> "${actions_file}"; }
run_import() { return 17; }
simulate_release_activation() {
  set -Eeuo pipefail
  run_import || return $?
  record_action source_pointer
  record_action web_pointer
  record_action api_restart
  record_action nginx_reload
}
if (simulate_release_activation); then
  echo "expected import failure to stop release activation" >&2
  exit 1
fi
[[ ! -s "${actions_file}" ]]
rm -f "${actions_file}"

echo "deploy-utils tests passed"
