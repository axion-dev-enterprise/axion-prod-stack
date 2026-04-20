#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

# shellcheck source=../lib/env.sh
source "$ROOT_DIR/scripts/lib/env.sh"

apt-get update
apt-get install -y certbot

certbot certonly \
  --non-interactive \
  --agree-tos \
  --register-unsafely-without-email \
  --standalone \
  --preferred-challenges http \
  --pre-hook "docker stop axion-platform-traefik-1 || true" \
  --post-hook "docker start axion-platform-traefik-1 || true" \
  --cert-name flow-tenants.axionenterprise.cloud \
  -d core.flow.axionenterprise.cloud \
  -d sales.flow.axionenterprise.cloud \
  -d support.flow.axionenterprise.cloud

echo "certificate ready at /etc/letsencrypt/live/flow-tenants.axionenterprise.cloud/"
