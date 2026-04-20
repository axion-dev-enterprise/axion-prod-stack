#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

set -a
source "$ENV_FILE"
set +a

install -m 0644 "$ROOT_DIR/infra/systemd/axion-restic-backup.service" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-restic-backup.timer" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-github-backup.service" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-github-backup.timer" /etc/systemd/system/

systemctl daemon-reload

if [[ -n "${CF_R2_ACCESS_KEY_ID:-}" && -n "${CF_R2_SECRET_ACCESS_KEY:-}" && -n "${CF_R2_ENDPOINT:-}" && -n "${RESTIC_PASSWORD:-}" ]]; then
  systemctl enable --now axion-restic-backup.timer
else
  echo "skipping axion-restic-backup.timer: R2/restic env incomplete"
fi

if [[ "${BACKUP_GITHUB_ENABLE:-false}" == "true" && -n "${BACKUP_GITHUB_TOKEN:-}" ]]; then
  systemctl enable --now axion-github-backup.timer
else
  echo "skipping axion-github-backup.timer: GitHub backup env incomplete"
fi
