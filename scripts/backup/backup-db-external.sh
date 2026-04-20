#!/usr/bin/env bash
set -euo pipefail
WORKDIR="${BACKUP_WORKDIR:-./backups}"
STAMP="$(date +%F_%H%M%S)"
OUT="$WORKDIR/db_$STAMP.sql.gz"
mkdir -p "$WORKDIR"
if [[ -z "${DB_DUMP_CMD:-}" ]]; then
  echo "DB_DUMP_CMD não definido."
  exit 1
fi
bash -lc "$DB_DUMP_CMD" > "$OUT"
echo "$OUT"
