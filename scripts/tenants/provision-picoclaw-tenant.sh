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

TENANT_SLUG="${1:-}"
TENANT_HOST="${2:-}"

if [[ -z "$TENANT_SLUG" ]]; then
  echo "usage: $0 <tenant-slug> [tenant-host]" >&2
  exit 1
fi

if [[ -z "$TENANT_HOST" ]]; then
  TENANT_HOST="${TENANT_SLUG}.$(read_env_value TENANT_BASE_DOMAIN)"
fi

AXION_ROOT_VALUE="$(read_env_value AXION_ROOT)"
PICOCLAW_IMAGE_VALUE="$(read_env_value PICOCLAW_IMAGE)"
PICOCLAW_GATEWAY_PORT_VALUE="$(read_env_value PICOCLAW_GATEWAY_PORT)"
PICOCLAW_TENANT_MEM_LIMIT_VALUE="$(read_env_value PICOCLAW_TENANT_MEM_LIMIT)"
PICOCLAW_TENANT_CPUS_VALUE="$(read_env_value PICOCLAW_TENANT_CPUS)"

export \
  OPENROUTER_API_KEY="$(read_env_value OPENROUTER_API_KEY)" \
  OPENROUTER_BASE_URL="$(read_env_value OPENROUTER_BASE_URL)" \
  BRAVE_API_KEY="$(read_env_value BRAVE_API_KEY)" \
  TAVILY_API_KEY="$(read_env_value TAVILY_API_KEY)" \
  TENANT_ADMIN_TOKEN="$(read_env_value TENANT_ADMIN_TOKEN)" \
  PICOCLAW_DEFAULT_MODEL="$(read_env_value PICOCLAW_DEFAULT_MODEL)" \
  PICOCLAW_DEFAULT_MAX_TOKENS="$(read_env_value PICOCLAW_DEFAULT_MAX_TOKENS)" \
  PICOCLAW_DEFAULT_CONTEXT_WINDOW="$(read_env_value PICOCLAW_DEFAULT_CONTEXT_WINDOW)" \
  PICOCLAW_TOOL_FEEDBACK="$(read_env_value PICOCLAW_TOOL_FEEDBACK)" \
  PICOCLAW_WEB_PROVIDER="$(read_env_value PICOCLAW_WEB_PROVIDER)" \
  PICOCLAW_ENABLE_MCP="$(read_env_value PICOCLAW_ENABLE_MCP)" \
  PICOCLAW_ENABLE_EXEC="$(read_env_value PICOCLAW_ENABLE_EXEC)" \
  FLOW_PUBLIC_URL="$(read_env_value FLOW_PUBLIC_URL)" \
  PICOCLAW_GATEWAY_PORT="${PICOCLAW_GATEWAY_PORT_VALUE:-18790}"

TENANT_DIR="${AXION_ROOT_VALUE}/tenants/${TENANT_SLUG}"
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
PICOCLAW_IMAGE=${PICOCLAW_IMAGE_VALUE}
PICOCLAW_GATEWAY_PORT=${PICOCLAW_GATEWAY_PORT_VALUE:-18790}
PICOCLAW_TENANT_MEM_LIMIT=${PICOCLAW_TENANT_MEM_LIMIT_VALUE:-768m}
PICOCLAW_TENANT_CPUS=${PICOCLAW_TENANT_CPUS_VALUE:-0.70}
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
