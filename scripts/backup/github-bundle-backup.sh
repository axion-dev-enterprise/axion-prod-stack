#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

set -a
source "$ENV_FILE"
set +a

if [[ "${BACKUP_GITHUB_ENABLE:-false}" != "true" ]]; then
  echo "github backup disabled"
  exit 0
fi

if [[ -z "${BACKUP_GITHUB_TOKEN:-}" ]]; then
  echo "BACKUP_GITHUB_TOKEN not configured" >&2
  exit 1
fi

STAMP="$(date +%F_%H%M%S)"
WORKDIR="${AXION_ROOT}/backups/github"
mkdir -p "$WORKDIR"
BUNDLE="${WORKDIR}/platform_${STAMP}.bundle"

git -C "$ROOT_DIR" bundle create "$BUNDLE" --all

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

git clone "https://x-access-token:${BACKUP_GITHUB_TOKEN}@github.com/${BACKUP_GITHUB_OWNER}/${BACKUP_GITHUB_REPO}.git" "$TMP_DIR/repo" >/dev/null 2>&1
git -C "$TMP_DIR/repo" checkout -B "$BACKUP_GITHUB_BRANCH"
mkdir -p "$TMP_DIR/repo/backups"
cp "$BUNDLE" "$TMP_DIR/repo/backups/"
git -C "$TMP_DIR/repo" add backups
git -C "$TMP_DIR/repo" commit -m "backup: ${STAMP}" >/dev/null 2>&1 || true
git -C "$TMP_DIR/repo" push origin "$BACKUP_GITHUB_BRANCH" >/dev/null 2>&1
