#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

set -a
source "$ENV_FILE"
set +a

STAMP="$(date +%F_%H%M%S)"
DUMP_DIR="${AXION_ROOT}/data/postgres-dumps"
mkdir -p "$DUMP_DIR"

docker exec "$(docker ps --filter name=postgres --format '{{.Names}}' | head -n1)" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  > "${DUMP_DIR}/postgres_${STAMP}.dump"

echo "${DUMP_DIR}/postgres_${STAMP}.dump"
