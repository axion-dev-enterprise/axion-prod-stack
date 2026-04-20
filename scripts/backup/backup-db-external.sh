#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

# shellcheck source=../lib/env.sh
source "$ROOT_DIR/scripts/lib/env.sh"

AXION_ROOT_VALUE="$(read_env_value "$ENV_FILE" AXION_ROOT)"
POSTGRES_USER_VALUE="$(read_env_value "$ENV_FILE" POSTGRES_USER)"
POSTGRES_DB_VALUE="$(read_env_value "$ENV_FILE" POSTGRES_DB)"

STAMP="$(date +%F_%H%M%S)"
DUMP_DIR="${AXION_ROOT_VALUE}/data/postgres-dumps"
mkdir -p "$DUMP_DIR"

docker exec "$(docker ps --filter name=postgres --format '{{.Names}}' | head -n1)" \
  pg_dump -U "$POSTGRES_USER_VALUE" -d "$POSTGRES_DB_VALUE" -Fc \
  > "${DUMP_DIR}/postgres_${STAMP}.dump"

echo "${DUMP_DIR}/postgres_${STAMP}.dump"
