#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/compose"
docker compose --env-file ../env/.env.example -f docker-compose.production.yml up -d --build
docker compose --env-file ../env/.env.example -f docker-compose.production.yml ps
