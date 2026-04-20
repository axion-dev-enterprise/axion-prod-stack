#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-https://router.example.com}"
curl -fsS "${BASE}/py/health"
echo
curl -fsS "${BASE}/node/health"
echo
