# AXION Multi-Tenant AI Stack

Stack de produção para operar `FLOW` e provisionar instâncias multi-tenant de `PicoClaw` com:

- isolamento por cliente
- workspace persistente
- memória/sessões persistentes
- cache (`Valkey`)
- fila/event stream (`NATS JetStream`)
- metadados e extensões futuras (`Postgres + pgvector`)
- edge com `Traefik`
- WAF na borda via `Cloudflare`
- observabilidade (`Grafana + Loki + Alloy + Uptime Kuma`)
- backup local + `restic` para `R2`
- backup de código/config em `GitHub`
- reprovisionamento rápido por scripts idempotentes

## Objetivo operacional

Esta stack foi desenhada para:

1. subir a plataforma base em um único VPS
2. provisionar um novo tenant PicoClaw em menos de 1 minuto quando a imagem já estiver disponível
3. restaurar a plataforma em um host novo a partir do repo + `.env` + backups

## Estrutura

- `compose/`: compose principal da plataforma
- `env/`: exemplo de variáveis e template de deploy
- `infra/`: Traefik, Loki, Alloy e systemd timers
- `scripts/deploy/`: bootstrap, deploy e reprovisionamento
- `scripts/backup/`: backup local, restic, bundle GitHub e restore
- `scripts/security/`: hardening do host
- `scripts/tenants/`: provisionamento e remoção de tenants PicoClaw
- `templates/picoclaw/`: template de `docker-compose` e render da `config.json`
- `docs/`: arquitetura, deploy e backup

## Fontes técnicas usadas

- PicoClaw oficial: https://github.com/sipeed/picoclaw
- Docker guide do PicoClaw: https://docs.picoclaw.io/
- OpenClaw oficial: https://github.com/openclaw/openclaw
- Docker install do OpenClaw: https://github.com/openclaw/openclaw/blob/main/docs/install/docker.md

## Status

O repo já inclui:

- compose da plataforma base
- gerador de tenant PicoClaw
- timers de backup
- scripts de bootstrap e reprovisionamento rápido

O próximo passo operacional é preencher `env/.env`, subir a base e chamar:

```bash
./scripts/tenants/provision-picoclaw-tenant.sh cliente-a bot.cliente-a.example.com
```
