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

AXION_ROOT_VALUE="$(read_env_value AXION_ROOT)"
TENANT_BASE_DOMAIN_VALUE="$(read_env_value TENANT_BASE_DOMAIN)"
PICOCLAW_IMAGE_VALUE="$(read_env_value PICOCLAW_IMAGE)"
PICOCLAW_GATEWAY_PORT_VALUE="$(read_env_value PICOCLAW_GATEWAY_PORT)"
PICOCLAW_TENANT_MEM_LIMIT_VALUE="$(read_env_value PICOCLAW_TENANT_MEM_LIMIT)"
PICOCLAW_TENANT_CPUS_VALUE="$(read_env_value PICOCLAW_TENANT_CPUS)"

export \
  OPENROUTER_API_KEY="$(read_env_value OPENROUTER_API_KEY)" \
  OPENROUTER_BASE_URL="$(read_env_value OPENROUTER_BASE_URL)" \
  FLOW_LLM_PROVIDER="$(read_env_value FLOW_LLM_PROVIDER)" \
  OLLAMA_CHAT_BASE_URL="$(read_env_value OLLAMA_CHAT_BASE_URL)" \
  OLLAMA_BASE_URL="$(read_env_value OLLAMA_BASE_URL)" \
  OLLAMA_API_KEY="$(read_env_value OLLAMA_API_KEY)" \
  OLLAMA_EMBED_MODEL="$(read_env_value OLLAMA_EMBED_MODEL)" \
  BRAVE_API_KEY="$(read_env_value BRAVE_API_KEY)" \
  TAVILY_API_KEY="$(read_env_value TAVILY_API_KEY)" \
  TENANT_ADMIN_TOKEN="$(read_env_value TENANT_ADMIN_TOKEN)" \
  PICOCLAW_DEFAULT_MODEL="$(read_env_value PICOCLAW_DEFAULT_MODEL)" \
  PICOCLAW_UPSTREAM_MODEL="$(read_env_value PICOCLAW_UPSTREAM_MODEL)" \
  PICOCLAW_DEFAULT_MAX_TOKENS="$(read_env_value PICOCLAW_DEFAULT_MAX_TOKENS)" \
  PICOCLAW_DEFAULT_CONTEXT_WINDOW="$(read_env_value PICOCLAW_DEFAULT_CONTEXT_WINDOW)" \
  PICOCLAW_TOOL_FEEDBACK="$(read_env_value PICOCLAW_TOOL_FEEDBACK)" \
  PICOCLAW_WEB_PROVIDER="$(read_env_value PICOCLAW_WEB_PROVIDER)" \
  PICOCLAW_ENABLE_MCP="$(read_env_value PICOCLAW_ENABLE_MCP)" \
  PICOCLAW_ENABLE_EXEC="$(read_env_value PICOCLAW_ENABLE_EXEC)" \
  FLOW_PUBLIC_URL="$(read_env_value FLOW_PUBLIC_URL)" \
  PICOCLAW_IMAGE="${PICOCLAW_IMAGE_VALUE}" \
  PICOCLAW_TENANT_MEM_LIMIT="${PICOCLAW_TENANT_MEM_LIMIT_VALUE:-768m}" \
  PICOCLAW_TENANT_CPUS="${PICOCLAW_TENANT_CPUS_VALUE:-0.70}" \
  PICOCLAW_GATEWAY_PORT="${PICOCLAW_GATEWAY_PORT_VALUE:-18790}"

shopt -s nullglob
for tenant_dir in "${AXION_ROOT_VALUE}"/tenants/*; do
  tenant_slug="$(basename "$tenant_dir")"
  if [[ ! "$tenant_slug" =~ ^[a-z0-9][a-z0-9-]{0,62}$ ]]; then
    echo "skip invalid tenant directory: $tenant_dir" >&2
    continue
  fi

  tenant_host="$(grep -E '^TENANT_HOST=' "$tenant_dir/tenant.env" 2>/dev/null | tail -n1 | cut -d= -f2- || true)"
  tenant_host="${tenant_host%\"}"
  tenant_host="${tenant_host#\"}"
  if [[ -z "$tenant_host" ]]; then
    tenant_host="${tenant_slug}.${TENANT_BASE_DOMAIN_VALUE}"
  fi

  data_dir="${tenant_dir}/data"
  workspace_dir="${data_dir}/workspace"
  mkdir -p "$data_dir" "$workspace_dir"

  export TENANT_SLUG="$tenant_slug" TENANT_HOST="$tenant_host"

  python3 "$ROOT_DIR/scripts/tenants/render_picoclaw_config.py" \
    "$tenant_slug" \
    "$tenant_host" \
    "${data_dir}/config.json"

  python3 "$ROOT_DIR/scripts/tenants/render_local_knowledge_workspace.py" \
    "$tenant_slug" \
    "$workspace_dir"

  cat > "${tenant_dir}/tenant.env" <<EOF
TENANT_SLUG=${tenant_slug}
TENANT_HOST=${tenant_host}
PICOCLAW_IMAGE=${PICOCLAW_IMAGE_VALUE}
PICOCLAW_GATEWAY_PORT=${PICOCLAW_GATEWAY_PORT_VALUE:-18790}
PICOCLAW_TENANT_MEM_LIMIT=${PICOCLAW_TENANT_MEM_LIMIT_VALUE:-768m}
PICOCLAW_TENANT_CPUS=${PICOCLAW_TENANT_CPUS_VALUE:-0.70}
EOF

  envsubst < "$ROOT_DIR/templates/picoclaw/docker-compose.tenant.yml" > "${tenant_dir}/docker-compose.yml"

  docker compose \
    --env-file "${tenant_dir}/tenant.env" \
    -f "${tenant_dir}/docker-compose.yml" \
    up -d

  if [[ -x "${workspace_dir}/tools/refresh_memory.sh" ]]; then
    docker exec "picoclaw-${tenant_slug}" sh -lc "sh /root/.picoclaw/workspace/tools/refresh_memory.sh" >/dev/null || true
  fi

  echo "reconciled ${tenant_slug} -> ${tenant_host}"
done
