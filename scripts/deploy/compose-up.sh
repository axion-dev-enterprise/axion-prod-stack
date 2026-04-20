#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "env file not found: $ENV_FILE" >&2
  exit 1
fi

read_env_value() {
  local key="$1"
  local value
  value="$(grep -E "^${key}=" "$ENV_FILE" | tail -n1 | cut -d= -f2- || true)"
  value="${value%\"}"
  value="${value#\"}"
  printf '%s' "${value:-}"
}

cd "$ROOT_DIR/compose"

EXTRA_ARGS=()
if [[ "$(read_env_value CF_ENABLE)" == "true" ]]; then
  EXTRA_ARGS+=(--profile edge)
fi
if [[ "$(read_env_value ENABLE_OBSERVABILITY)" == "true" ]]; then
  EXTRA_ARGS+=(--profile observability)
fi
if [[ "$(read_env_value ENABLE_STATUS)" == "true" ]]; then
  EXTRA_ARGS+=(--profile status)
fi

docker compose --env-file "$ENV_FILE" -f docker-compose.production.yml "${EXTRA_ARGS[@]}" up -d
docker compose --env-file "$ENV_FILE" -f docker-compose.production.yml "${EXTRA_ARGS[@]}" ps
