#!/usr/bin/env bash
set -euo pipefail
SRC="${1:-${BACKUP_WORKDIR:-./backups}}"
BUCKET="${CF_R2_BUCKET:-axion-backups}"
rclone sync "$SRC" "r2:${BUCKET}" --fast-list --transfers 8 --checkers 16 --s3-no-check-bucket
echo "Upload concluído."
