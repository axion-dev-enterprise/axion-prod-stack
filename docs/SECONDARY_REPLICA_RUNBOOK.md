# Secondary Replica Runbook

## Objetivo

Subir uma segunda maquina self-host capaz de:

- restaurar a plataforma a partir do GitHub + restic
- assumir trafego via Cloudflare
- manter tenants e paineis alinhados

## Pre-requisitos

- Linux amd64
- Docker + Compose
- acesso ao repositório `axion-prod-stack`
- `env/.env` com `CF_API_TOKEN`, `CF_ZONE_ID`, `CF_R2_*`, `RESTIC_PASSWORD`

## Bootstrap

```bash
git clone https://github.com/axion-dev-enterprise/axion-prod-stack.git /opt/axion/platform
cd /opt/axion/platform
./scripts/deploy/bootstrap-secondary-restore.sh /opt/axion/platform /opt/axion-restore
```

## Export da primaria

```bash
./scripts/export/export-host-config.sh
```

## Cutover

```bash
./scripts/cloudflare/apply-dns-cutover.sh docs/cloudflare-dns-manifest.json <IP-DA-REPLICA>
```

## Validacao

- `docker ps`
- `systemctl status axion-*`
- `status.axionenterprise.cloud`
- `grafana.axionenterprise.cloud`
- `*.flow.axionenterprise.cloud`
