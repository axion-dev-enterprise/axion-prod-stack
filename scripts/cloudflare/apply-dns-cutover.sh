#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"
MANIFEST_FILE="${1:-$ROOT_DIR/docs/cloudflare-dns-manifest.json}"
TARGET_IP="${2:-}"

# shellcheck source=../lib/env.sh
source "$ROOT_DIR/scripts/lib/env.sh"

CF_API_TOKEN_VALUE="$(read_env_value "$ENV_FILE" CF_API_TOKEN)"
CF_ZONE_ID_VALUE="$(read_env_value "$ENV_FILE" CF_ZONE_ID)"

if [[ -z "$CF_API_TOKEN_VALUE" || -z "$CF_ZONE_ID_VALUE" ]]; then
  echo "cloudflare cutover skipped: CF_API_TOKEN/CF_ZONE_ID missing" >&2
  exit 0
fi

if [[ -z "$TARGET_IP" ]]; then
  TARGET_IP="$(read_env_value "$ENV_FILE" SECONDARY_ORIGIN_IP)"
fi

if [[ -z "$TARGET_IP" ]]; then
  echo "target ip missing" >&2
  exit 1
fi

python3 - "$MANIFEST_FILE" "$TARGET_IP" "$CF_ZONE_ID_VALUE" "$CF_API_TOKEN_VALUE" <<'PY'
import json
import sys
import urllib.request

manifest_path, target_ip, zone_id, token = sys.argv[1:5]
records = json.load(open(manifest_path, encoding="utf-8"))["records"]

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

def request(method, url, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)

base = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
existing = request("GET", base + "?per_page=1000")["result"]

for desired in records:
    body = {
        "type": "A",
        "name": desired["name"],
        "content": target_ip,
        "proxied": desired.get("proxied", True),
        "ttl": desired.get("ttl", 1),
    }
    match = next((r for r in existing if r["name"] == desired["name"] and r["type"] == "A"), None)
    if match:
      result = request("PUT", f"{base}/{match['id']}", body)
      print(f"updated {desired['name']}: {result['success']}")
    else:
      result = request("POST", base, body)
      print(f"created {desired['name']}: {result['success']}")
PY
