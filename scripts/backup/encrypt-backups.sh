#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-}"
if [[ -z "$TARGET" || -z "${BACKUP_PASSPHRASE:-}" ]]; then
  echo "Uso: BACKUP_PASSPHRASE=... $0 arquivo"
  exit 1
fi
openssl enc -aes-256-cbc -pbkdf2 -salt -in "$TARGET" -out "$TARGET.enc" -pass env:BACKUP_PASSPHRASE
echo "$TARGET.enc"
