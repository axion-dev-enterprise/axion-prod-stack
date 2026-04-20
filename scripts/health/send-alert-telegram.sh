#!/usr/bin/env bash
set -euo pipefail
MSG="${1:-AXION alert}"
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  echo "Telegram não configurado."
  exit 1
fi
curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"   -H "Content-Type: application/json"   -d "{"chat_id":"${TELEGRAM_CHAT_ID}","text":"${MSG}"}"
