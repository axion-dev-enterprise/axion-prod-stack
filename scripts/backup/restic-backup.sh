#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

set -a
source "$ENV_FILE"
set +a

export AWS_ACCESS_KEY_ID="${CF_R2_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${CF_R2_SECRET_ACCESS_KEY}"
export RESTIC_PASSWORD
export RESTIC_REPOSITORY="s3:${CF_R2_ENDPOINT}/${CF_R2_BUCKET}"

restic snapshots >/dev/null 2>&1 || restic init

"$ROOT_DIR/scripts/backup/backup-db-external.sh" >/dev/null

restic backup \
  "${AXION_ROOT}/platform" \
  "${AXION_ROOT}/tenants" \
  "${AXION_ROOT}/data" \
  "${AXION_ROOT}/runtime" \
  "${AXION_ROOT}/backups"

restic forget \
  --prune \
  --keep-daily "${RESTIC_RETENTION_DAILY}" \
  --keep-weekly "${RESTIC_RETENTION_WEEKLY}" \
  --keep-monthly "${RESTIC_RETENTION_MONTHLY}"
