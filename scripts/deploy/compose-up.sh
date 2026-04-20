#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "env file not found: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

cd "$ROOT_DIR/compose"

EXTRA_ARGS=()
if [[ "${CF_ENABLE:-false}" == "true" ]]; then
  EXTRA_ARGS+=(--profile edge)
fi
if [[ "${ENABLE_OBSERVABILITY:-false}" == "true" ]]; then
  EXTRA_ARGS+=(--profile observability)
fi
if [[ "${ENABLE_STATUS:-false}" == "true" ]]; then
  EXTRA_ARGS+=(--profile status)
fi

docker compose --env-file "$ENV_FILE" -f docker-compose.production.yml "${EXTRA_ARGS[@]}" up -d
docker compose --env-file "$ENV_FILE" -f docker-compose.production.yml "${EXTRA_ARGS[@]}" ps
