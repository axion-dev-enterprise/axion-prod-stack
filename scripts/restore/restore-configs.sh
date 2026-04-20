#!/usr/bin/env bash
set -euo pipefail
ARCHIVE="${1:-}"
TARGET="${2:-./restore-output}"
if [[ -z "$ARCHIVE" ]]; then
  echo "Uso: $0 arquivo.tar.gz [destino]"
  exit 1
fi
mkdir -p "$TARGET"
tar -xzf "$ARCHIVE" -C "$TARGET"
echo "Restore concluído em $TARGET"
