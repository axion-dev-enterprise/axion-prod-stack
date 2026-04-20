#!/usr/bin/env bash
set -euo pipefail
curl -fsSL https://rclone.org/install.sh | sudo bash
rclone version
