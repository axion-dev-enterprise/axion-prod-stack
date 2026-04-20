#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

# shellcheck source=../lib/env.sh
source "$ROOT_DIR/scripts/lib/env.sh"

if ! env_value_is_true "$ENV_FILE" BACKUP_GITHUB_ENABLE; then
  echo "github backup disabled"
  exit 0
fi

BACKUP_GITHUB_TOKEN_VALUE="$(read_env_value "$ENV_FILE" BACKUP_GITHUB_TOKEN)"
BACKUP_GITHUB_OWNER_VALUE="$(read_env_value "$ENV_FILE" BACKUP_GITHUB_OWNER)"
BACKUP_GITHUB_REPO_VALUE="$(read_env_value "$ENV_FILE" BACKUP_GITHUB_REPO)"
BACKUP_GITHUB_BRANCH_VALUE="$(read_env_value "$ENV_FILE" BACKUP_GITHUB_BRANCH)"
AXION_ROOT_VALUE="$(read_env_value "$ENV_FILE" AXION_ROOT)"

if [[ -z "$BACKUP_GITHUB_TOKEN_VALUE" ]]; then
  echo "BACKUP_GITHUB_TOKEN not configured" >&2
  exit 1
fi

STAMP="$(date +%F_%H%M%S)"
WORKDIR="${AXION_ROOT_VALUE}/backups/github"
mkdir -p "$WORKDIR"
BUNDLE="${WORKDIR}/platform_${STAMP}.bundle"

git -C "$ROOT_DIR" bundle create "$BUNDLE" --all

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

git clone "https://x-access-token:${BACKUP_GITHUB_TOKEN_VALUE}@github.com/${BACKUP_GITHUB_OWNER_VALUE}/${BACKUP_GITHUB_REPO_VALUE}.git" "$TMP_DIR/repo" >/dev/null 2>&1
git -C "$TMP_DIR/repo" checkout -B "$BACKUP_GITHUB_BRANCH_VALUE"
mkdir -p "$TMP_DIR/repo/backups"
cp "$BUNDLE" "$TMP_DIR/repo/backups/"
git -C "$TMP_DIR/repo" add -f backups
git -C "$TMP_DIR/repo" commit -m "backup: ${STAMP}" >/dev/null 2>&1 || true
git -C "$TMP_DIR/repo" push origin "$BACKUP_GITHUB_BRANCH_VALUE" >/dev/null 2>&1
