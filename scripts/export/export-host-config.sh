#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/env/.env}"
STAMP="$(date +%F_%H%M%S)"
OUT_DIR="${1:-${ROOT_DIR}/exports/host-${STAMP}}"

mkdir -p "$OUT_DIR"

{
  echo "# AXION host export"
  echo "generated_at=$(date -Is)"
  echo "hostname=$(hostname)"
  echo "kernel=$(uname -a)"
} > "$OUT_DIR/metadata.txt"

if [[ -f "$ENV_FILE" ]]; then
  python3 - "$ENV_FILE" "$OUT_DIR/env.redacted" <<'PY'
from pathlib import Path
import re
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
secret_re = re.compile(r"(TOKEN|PASSWORD|SECRET|KEY)", re.IGNORECASE)
lines = []
for line in src.read_text(encoding="utf-8").splitlines():
    if "=" not in line or line.lstrip().startswith("#"):
        lines.append(line)
        continue
    key, value = line.split("=", 1)
    if secret_re.search(key):
        lines.append(f"{key}=<redacted>")
    else:
        lines.append(f"{key}={value}")
dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
fi

docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' > "$OUT_DIR/docker-ps.txt"
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}' > "$OUT_DIR/docker-stats.txt"
systemctl list-unit-files 'axion-*' > "$OUT_DIR/systemd-units.txt"
systemctl --no-pager --full status axion-docker-firewall.service axion-github-backup.timer axion-restic-backup.timer axion-restic-verify.timer > "$OUT_DIR/systemd-status.txt" 2>&1 || true
iptables -S DOCKER-USER > "$OUT_DIR/docker-user-rules.txt"
ss -tulpn > "$OUT_DIR/listeners.txt"
free -h > "$OUT_DIR/free.txt"
cat /proc/loadavg > "$OUT_DIR/loadavg.txt"

tar -czf "${OUT_DIR}.tar.gz" -C "$(dirname "$OUT_DIR")" "$(basename "$OUT_DIR")"
echo "${OUT_DIR}.tar.gz"
