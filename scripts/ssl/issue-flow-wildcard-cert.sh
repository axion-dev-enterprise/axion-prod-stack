#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"

# shellcheck source=../lib/env.sh
source "$ROOT_DIR/scripts/lib/env.sh"

CF_API_TOKEN_VALUE="$(read_env_value "$ENV_FILE" CF_API_TOKEN)"

if [[ -z "$CF_API_TOKEN_VALUE" ]]; then
  echo "CF_API_TOKEN missing" >&2
  exit 1
fi

apt-get update
apt-get install -y certbot python3-certbot-dns-cloudflare

install -d -m 0700 /root/.secrets/certbot
cat > /root/.secrets/certbot/cloudflare.ini <<EOF
dns_cloudflare_api_token = ${CF_API_TOKEN_VALUE}
EOF
chmod 600 /root/.secrets/certbot/cloudflare.ini

certbot certonly \
  --non-interactive \
  --agree-tos \
  --register-unsafely-without-email \
  --dns-cloudflare \
  --dns-cloudflare-credentials /root/.secrets/certbot/cloudflare.ini \
  --dns-cloudflare-propagation-seconds 30 \
  --cert-name flow.axionenterprise.cloud \
  -d flow.axionenterprise.cloud \
  -d '*.flow.axionenterprise.cloud'

echo "certificate ready at /etc/letsencrypt/live/flow.axionenterprise.cloud/"
