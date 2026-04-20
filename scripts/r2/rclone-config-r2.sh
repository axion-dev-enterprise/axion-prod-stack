#!/usr/bin/env bash
set -euo pipefail
RCLONE_DIR="${HOME}/.config/rclone"
mkdir -p "$RCLONE_DIR"
cat > "$RCLONE_DIR/rclone.conf" <<EOF
[r2]
type = s3
provider = Cloudflare
access_key_id = ${CF_R2_ACCESS_KEY_ID}
secret_access_key = ${CF_R2_SECRET_ACCESS_KEY}
endpoint = ${CF_R2_ENDPOINT}
region = ${CF_R2_REGION:-auto}
acl = private
no_check_bucket = true
EOF
chmod 600 "$RCLONE_DIR/rclone.conf"
echo "rclone configurado."
