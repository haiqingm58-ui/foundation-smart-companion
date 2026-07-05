#!/usr/bin/env bash

wait_for_http() {
  local url="$1"
  local max_attempts="${2:-20}"
  local delay_seconds="${3:-1}"
  local attempt

  for ((attempt = 1; attempt <= max_attempts; attempt += 1)); do
    if curl -fsS --connect-timeout 3 --max-time 10 "${url}" >/dev/null; then
      return 0
    fi
    if ((attempt < max_attempts)); then
      sleep "${delay_seconds}"
    fi
  done

  echo "Health check failed after ${max_attempts} attempts: ${url}" >&2
  return 1
}

verify_page_contains() {
  local url="$1"
  local expected_text="$2"

  curl -fsSL --connect-timeout 3 --max-time 15 "${url}" | grep -Fq "${expected_text}"
}
