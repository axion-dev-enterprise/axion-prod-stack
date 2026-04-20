#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-/opt/axion/platform}"
RESTORE_TARGET="${2:-/opt/axion-restore}"

"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bootstrap-server.sh" "$REPO_DIR"

cd "$REPO_DIR"
find scripts -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod +x {} +

if [[ ! -f "$REPO_DIR/env/.env" ]]; then
  echo "env missing at $REPO_DIR/env/.env" >&2
  exit 1
fi

./scripts/backup/restic-restore.sh "$RESTORE_TARGET" latest || true

if [[ -d "$RESTORE_TARGET/opt/axion" ]]; then
  rsync -a --delete "$RESTORE_TARGET/opt/axion/" /opt/axion/
fi

./scripts/deploy/compose-up.sh
./scripts/deploy/install-systemd-units.sh

echo "secondary bootstrap complete"
