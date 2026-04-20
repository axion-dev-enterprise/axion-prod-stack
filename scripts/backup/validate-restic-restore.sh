#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

# shellcheck source=../lib/env.sh
source "$ROOT_DIR/scripts/lib/env.sh"

CF_R2_ACCESS_KEY_ID="$(read_env_value "$ENV_FILE" CF_R2_ACCESS_KEY_ID)"
CF_R2_SECRET_ACCESS_KEY="$(read_env_value "$ENV_FILE" CF_R2_SECRET_ACCESS_KEY)"
CF_R2_ENDPOINT="$(read_env_value "$ENV_FILE" CF_R2_ENDPOINT)"
CF_R2_BUCKET="$(read_env_value "$ENV_FILE" CF_R2_BUCKET)"
RESTIC_PASSWORD_VALUE="$(read_env_value "$ENV_FILE" RESTIC_PASSWORD)"
AXION_ROOT_VALUE="$(read_env_value "$ENV_FILE" AXION_ROOT)"

if [[ -z "$CF_R2_ACCESS_KEY_ID" || -z "$CF_R2_SECRET_ACCESS_KEY" || -z "$CF_R2_ENDPOINT" || -z "$CF_R2_BUCKET" || -z "$RESTIC_PASSWORD_VALUE" || -z "$AXION_ROOT_VALUE" ]]; then
  echo "restic validation skipped: env incomplete" >&2
  exit 0
fi

export AWS_ACCESS_KEY_ID="$CF_R2_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$CF_R2_SECRET_ACCESS_KEY"
export RESTIC_PASSWORD="$RESTIC_PASSWORD_VALUE"
export RESTIC_REPOSITORY="s3:${CF_R2_ENDPOINT}/${CF_R2_BUCKET}"

TMP_DIR="$(mktemp -d /tmp/axion-restic-verify.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

restic snapshots latest >/dev/null
restic restore latest --target "$TMP_DIR" >/dev/null

RESTORED_ROOT="$TMP_DIR${AXION_ROOT_VALUE}"
test -f "$RESTORED_ROOT/platform/compose/docker-compose.production.yml"
test -f "$RESTORED_ROOT/platform/env/.env"
test -d "$RESTORED_ROOT/data"
test -d "$RESTORED_ROOT/runtime"

find "$RESTORED_ROOT/platform/compose" -maxdepth 1 -name 'docker-compose.production.yml' | grep -q .

echo "restic restore validation succeeded: $RESTORED_ROOT"
