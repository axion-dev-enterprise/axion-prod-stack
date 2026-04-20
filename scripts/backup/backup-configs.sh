#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${BACKUP_WORKDIR:-$ROOT_DIR/backups}"
STAMP="$(date +%F_%H%M%S)"
OUT="$WORKDIR/configs_$STAMP.tar.gz"
mkdir -p "$WORKDIR"
tar -czf "$OUT" "$ROOT_DIR/compose" "$ROOT_DIR/infra" "$ROOT_DIR/services" "$ROOT_DIR/docs" "$ROOT_DIR/scripts" "$ROOT_DIR/env"
echo "$OUT"
