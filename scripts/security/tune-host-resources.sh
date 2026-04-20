#!/usr/bin/env bash
set -euo pipefail

SWAP_SIZE_GB="${1:-4}"
SWAP_FILE="/swapfile"

if [[ ! -f "$SWAP_FILE" ]]; then
  fallocate -l "${SWAP_SIZE_GB}G" "$SWAP_FILE" || dd if=/dev/zero of="$SWAP_FILE" bs=1M count=$((SWAP_SIZE_GB * 1024))
  chmod 600 "$SWAP_FILE"
  mkswap "$SWAP_FILE"
  swapon "$SWAP_FILE"
fi

grep -q "$SWAP_FILE" /etc/fstab || echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab

cat >/etc/sysctl.d/99-axion-tuning.conf <<'EOF'
vm.swappiness=10
vm.vfs_cache_pressure=50
net.core.somaxconn=4096
fs.inotify.max_user_watches=524288
fs.inotify.max_user_instances=1024
EOF

sysctl --system

echo "host tuning applied"
