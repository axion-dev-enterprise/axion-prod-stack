#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

WORKDIR="${BACKUP_WORKDIR:-${AXION_ROOT:-$ROOT_DIR}/backups/local}"
STAMP="$(date +%F_%H%M%S)"
OUT="$WORKDIR/configs_$STAMP.tar.gz"

mkdir -p "$WORKDIR"
tar -czf "$OUT" \
  "$ROOT_DIR/compose" \
  "$ROOT_DIR/infra" \
  "$ROOT_DIR/scripts" \
  "$ROOT_DIR/templates" \
  "$ROOT_DIR/docs" \
  "$ROOT_DIR/env/.env.example"

echo "$OUT"
