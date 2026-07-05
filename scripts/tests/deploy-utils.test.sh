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

echo "deploy-utils tests passed"
