#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

install -m 0644 "$ROOT_DIR/infra/systemd/axion-restic-backup.service" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-restic-backup.timer" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-github-backup.service" /etc/systemd/system/
install -m 0644 "$ROOT_DIR/infra/systemd/axion-github-backup.timer" /etc/systemd/system/

systemctl daemon-reload
systemctl enable --now axion-restic-backup.timer
systemctl enable --now axion-github-backup.timer
