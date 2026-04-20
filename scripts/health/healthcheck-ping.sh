#!/usr/bin/env bash
set -euo pipefail
URL="${HEALTHCHECKS_PING_URL:-}"
STATE="${1:-success}"
if [[ -z "$URL" ]]; then
  echo "HEALTHCHECKS_PING_URL não definido."
  exit 1
fi
case "$STATE" in
  success) curl -fsS -m 10 --retry 3 "$URL" ;;
  fail) curl -fsS -m 10 --retry 3 "$URL/fail" ;;
  start) curl -fsS -m 10 --retry 3 "$URL/start" ;;
  *) echo "use success|fail|start"; exit 1 ;;
esac
