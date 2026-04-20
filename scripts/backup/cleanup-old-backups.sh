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
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

find "$WORKDIR" -type f -mtime +"$RETENTION_DAYS" -delete
