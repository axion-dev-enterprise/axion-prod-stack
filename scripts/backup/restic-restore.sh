#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"
TARGET_DIR="${1:-/opt/axion-restore}"
SNAPSHOT="${2:-latest}"

set -a
source "$ENV_FILE"
set +a

export AWS_ACCESS_KEY_ID="${CF_R2_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${CF_R2_SECRET_ACCESS_KEY}"
export RESTIC_PASSWORD
export RESTIC_REPOSITORY="s3:${CF_R2_ENDPOINT}/${CF_R2_BUCKET}"

mkdir -p "$TARGET_DIR"
restic restore "$SNAPSHOT" --target "$TARGET_DIR"
