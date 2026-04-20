#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"
TARGET_DIR="${1:-/opt/axion-restore}"
SNAPSHOT="${2:-latest}"

# shellcheck source=../lib/env.sh
source "$ROOT_DIR/scripts/lib/env.sh"

export AWS_ACCESS_KEY_ID="$(read_env_value "$ENV_FILE" CF_R2_ACCESS_KEY_ID)"
export AWS_SECRET_ACCESS_KEY="$(read_env_value "$ENV_FILE" CF_R2_SECRET_ACCESS_KEY)"
export RESTIC_PASSWORD="$(read_env_value "$ENV_FILE" RESTIC_PASSWORD)"
export RESTIC_REPOSITORY="s3:$(read_env_value "$ENV_FILE" CF_R2_ENDPOINT)/$(read_env_value "$ENV_FILE" CF_R2_BUCKET)"

mkdir -p "$TARGET_DIR"
restic restore "$SNAPSHOT" --target "$TARGET_DIR"
