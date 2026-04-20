#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

# shellcheck source=../lib/env.sh
source "$ROOT_DIR/scripts/lib/env.sh"

export AWS_ACCESS_KEY_ID="$(read_env_value "$ENV_FILE" CF_R2_ACCESS_KEY_ID)"
export AWS_SECRET_ACCESS_KEY="$(read_env_value "$ENV_FILE" CF_R2_SECRET_ACCESS_KEY)"
export RESTIC_PASSWORD="$(read_env_value "$ENV_FILE" RESTIC_PASSWORD)"
export RESTIC_REPOSITORY="s3:$(read_env_value "$ENV_FILE" CF_R2_ENDPOINT)/$(read_env_value "$ENV_FILE" CF_R2_BUCKET)"
AXION_ROOT_VALUE="$(read_env_value "$ENV_FILE" AXION_ROOT)"
RESTIC_RETENTION_DAILY_VALUE="$(read_env_value "$ENV_FILE" RESTIC_RETENTION_DAILY)"
RESTIC_RETENTION_WEEKLY_VALUE="$(read_env_value "$ENV_FILE" RESTIC_RETENTION_WEEKLY)"
RESTIC_RETENTION_MONTHLY_VALUE="$(read_env_value "$ENV_FILE" RESTIC_RETENTION_MONTHLY)"

restic snapshots >/dev/null 2>&1 || restic init

"$ROOT_DIR/scripts/backup/backup-db-external.sh" >/dev/null

restic backup \
  "${AXION_ROOT_VALUE}/platform" \
  "${AXION_ROOT_VALUE}/tenants" \
  "${AXION_ROOT_VALUE}/data" \
  "${AXION_ROOT_VALUE}/runtime" \
  "${AXION_ROOT_VALUE}/backups"

restic forget \
  --prune \
  --keep-daily "${RESTIC_RETENTION_DAILY_VALUE:-14}" \
  --keep-weekly "${RESTIC_RETENTION_WEEKLY_VALUE:-8}" \
  --keep-monthly "${RESTIC_RETENTION_MONTHLY_VALUE:-6}"
