#!/usr/bin/env bash
set -euo pipefail

apt-get update
apt-get install -y ufw fail2ban

ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw --force enable

systemctl enable --now fail2ban
