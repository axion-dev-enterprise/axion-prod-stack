# Backup e R2

Camadas:
- Git: configs, scripts, docs
- backup configs: compose, infra, services, env
- dump DB externo: via `DB_DUMP_CMD`
- criptografia opcional: `encrypt-backups.sh`
- sync: rclone -> Cloudflare R2

Scripts:
- scripts/backup/backup-configs.sh
- scripts/backup/backup-db-external.sh
- scripts/backup/encrypt-backups.sh
- scripts/backup/cleanup-old-backups.sh
- scripts/r2/rclone-config-r2.sh
- scripts/r2/r2-sync-push.sh
- scripts/r2/r2-sync-pull.sh
