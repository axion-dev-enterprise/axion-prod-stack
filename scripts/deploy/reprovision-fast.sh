#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

if [[ ! -d "$ROOT_DIR/.git" ]]; then
  echo "git repo required for fast reprovision" >&2
  exit 1
fi

git -C "$ROOT_DIR" fetch --all --prune
git -C "$ROOT_DIR" reset --hard origin/main
"$ROOT_DIR/scripts/deploy/compose-up.sh"
