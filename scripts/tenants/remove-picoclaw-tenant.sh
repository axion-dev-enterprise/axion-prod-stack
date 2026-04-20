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

TENANT_SLUG="${1:-}"

if [[ -z "$TENANT_SLUG" ]]; then
  echo "usage: $0 <tenant-slug>" >&2
  exit 1
fi

TENANT_DIR="${AXION_ROOT}/tenants/${TENANT_SLUG}"

if [[ ! -f "${TENANT_DIR}/docker-compose.yml" ]]; then
  echo "tenant compose not found: ${TENANT_DIR}/docker-compose.yml" >&2
  exit 1
fi

docker compose \
  --env-file "${TENANT_DIR}/tenant.env" \
  -f "${TENANT_DIR}/docker-compose.yml" \
  down
