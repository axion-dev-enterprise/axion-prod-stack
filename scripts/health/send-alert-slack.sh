#!/usr/bin/env bash
set -euo pipefail
MSG="${1:-AXION alert}"
if [[ -z "${SLACK_WEBHOOK_URL:-}" ]]; then
  echo "Slack não configurado."
  exit 1
fi
curl -fsS -X POST "$SLACK_WEBHOOK_URL" -H "Content-Type: application/json" -d "{"text":"${MSG}"}"
