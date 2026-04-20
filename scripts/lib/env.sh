#!/usr/bin/env bash
set -euo pipefail

read_env_value() {
  local env_file="$1"
  local key="$2"
  local value

  if [[ ! -f "$env_file" ]]; then
    printf '%s' ""
    return 0
  fi

  value="$(grep -E "^${key}=" "$env_file" | tail -n1 | cut -d= -f2- || true)"
  value="${value%\"}"
  value="${value#\"}"
  value="${value#" "}"
  printf '%s' "${value:-}"
}

env_value_is_true() {
  local env_file="$1"
  local key="$2"
  [[ "$(read_env_value "$env_file" "$key")" == "true" ]]
}
