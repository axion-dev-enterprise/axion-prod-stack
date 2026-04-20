#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-/opt/axion/platform}"

apt-get update
apt-get install -y \
  ca-certificates \
  curl \
  git \
  gnupg \
  lsb-release \
  jq \
  unzip \
  python3 \
  python3-venv \
  gettext-base \
  restic \
  ufw \
  fail2ban

if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list >/dev/null
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

install -d -m 0755 /opt/axion /opt/axion/data /opt/axion/runtime /opt/axion/backups /opt/axion/tenants

if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone https://github.com/axion-dev-enterprise/axion-prod-stack.git "$REPO_DIR"
else
  git -C "$REPO_DIR" fetch --all --prune
  git -C "$REPO_DIR" reset --hard origin/main
fi

find "$REPO_DIR/scripts" -type f -name '*.sh' -exec chmod +x {} +
find "$REPO_DIR/scripts" -type f -name '*.py' -exec chmod +x {} +

echo "bootstrap complete: $REPO_DIR"
