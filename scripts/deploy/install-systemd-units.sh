#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

# shellcheck source=../lib/env.sh
source "$ROOT_DIR/scripts/lib/env.sh"

install -m 0644 "$ROOT_DIR/infra/systemd/axion-restic-backup.service" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-restic-backup.timer" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-restic-verify.service" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-restic-verify.timer" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-github-backup.service" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-github-backup.timer" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-docker-firewall.service" /etc/systemd/system/

systemctl daemon-reload
systemctl enable --now axion-docker-firewall.service

if [[ -n "$(read_env_value "$ENV_FILE" CF_R2_ACCESS_KEY_ID)" && -n "$(read_env_value "$ENV_FILE" CF_R2_SECRET_ACCESS_KEY)" && -n "$(read_env_value "$ENV_FILE" CF_R2_ENDPOINT)" && -n "$(read_env_value "$ENV_FILE" RESTIC_PASSWORD)" ]]; then
  systemctl enable --now axion-restic-backup.timer
  systemctl enable --now axion-restic-verify.timer
else
  echo "skipping restic timers: R2/restic env incomplete"
fi

if env_value_is_true "$ENV_FILE" BACKUP_GITHUB_ENABLE && [[ -n "$(read_env_value "$ENV_FILE" BACKUP_GITHUB_TOKEN)" ]]; then
  systemctl enable --now axion-github-backup.timer
else
  echo "skipping axion-github-backup.timer: GitHub backup env incomplete"
fi
