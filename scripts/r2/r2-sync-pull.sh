#!/usr/bin/env bash
set -euo pipefail
DST="${1:-./backups-restored}"
BUCKET="${CF_R2_BUCKET:-axion-backups}"
mkdir -p "$DST"
rclone sync "r2:${BUCKET}" "$DST" --fast-list --transfers 8 --checkers 16 --s3-no-check-bucket
echo "Download concluído."
