#!/usr/bin/env bash
set -euo pipefail
WORKDIR="${BACKUP_WORKDIR:-./backups}"
RETENTION="${BACKUP_RETENTION_DAYS:-14}"
find "$WORKDIR" -type f -mtime +"$RETENTION" -print -delete
