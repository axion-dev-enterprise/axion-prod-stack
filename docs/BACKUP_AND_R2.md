# Backup And R2

## Estratégia

A stack usa três camadas:

1. snapshot local em `/opt/axion/backups`
2. backup criptografado com `restic` em `Cloudflare R2`
3. `git bundle` enviado para branch de backup no GitHub

## O que entra

- repo da plataforma
- diretórios de tenants
- dados persistentes em `/opt/axion/data`
- runtime state útil em `/opt/axion/runtime`
- dumps lógicos do Postgres

## Execução manual

```bash
./scripts/backup/backup-configs.sh
./scripts/backup/backup-db-external.sh
./scripts/backup/restic-backup.sh
./scripts/backup/github-bundle-backup.sh
```

## Restore

```bash
./scripts/backup/restic-restore.sh /opt/axion-restore latest
```

Depois:

1. recoloque `env/.env`
2. restaure os diretórios para `/opt/axion`
3. rode `./scripts/deploy/compose-up.sh`

## Timers

- `axion-restic-backup.timer`: a cada 30 minutos
- `axion-github-backup.timer`: diariamente
