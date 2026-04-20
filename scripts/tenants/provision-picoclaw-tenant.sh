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
TENANT_HOST="${2:-}"

if [[ -z "$TENANT_SLUG" ]]; then
  echo "usage: $0 <tenant-slug> [tenant-host]" >&2
  exit 1
fi

if [[ -z "$TENANT_HOST" ]]; then
  TENANT_HOST="${TENANT_SLUG}.${TENANT_BASE_DOMAIN}"
fi

TENANT_DIR="${AXION_ROOT}/tenants/${TENANT_SLUG}"
DATA_DIR="${TENANT_DIR}/data"
WORKSPACE_DIR="${DATA_DIR}/workspace"

mkdir -p "$DATA_DIR" "$WORKSPACE_DIR"

export TENANT_SLUG TENANT_HOST

python3 "$ROOT_DIR/scripts/tenants/render_picoclaw_config.py" \
  "$TENANT_SLUG" \
  "$TENANT_HOST" \
  "${DATA_DIR}/config.json"

cat > "${TENANT_DIR}/tenant.env" <<EOF
TENANT_SLUG=${TENANT_SLUG}
TENANT_HOST=${TENANT_HOST}
PICOCLAW_IMAGE=${PICOCLAW_IMAGE}
PICOCLAW_GATEWAY_PORT=${PICOCLAW_GATEWAY_PORT}
EOF

envsubst < "$ROOT_DIR/templates/picoclaw/docker-compose.tenant.yml" > "${TENANT_DIR}/docker-compose.yml"

docker compose \
  --env-file "${TENANT_DIR}/tenant.env" \
  -f "${TENANT_DIR}/docker-compose.yml" \
  up -d

docker compose \
  --env-file "${TENANT_DIR}/tenant.env" \
  -f "${TENANT_DIR}/docker-compose.yml" \
  ps
