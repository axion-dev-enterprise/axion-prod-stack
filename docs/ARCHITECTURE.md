# Architecture

## Base platform

Serviços permanentes:

- `Traefik`: roteamento HTTP interno da plataforma
- `cloudflared`: borda pública opcional via Cloudflare Tunnel
- `Valkey`: cache, locks e coordenação rápida
- `NATS JetStream`: fila/event stream para automações e jobs
- `Postgres + pgvector`: metadados, feature flags, memória futura e indexação
- `Grafana + Loki + Alloy`: logs e observabilidade
- `Uptime Kuma`: smoke checks da plataforma e dos tenants

## Tenant model

Cada cliente roda em um diretório isolado:

```text
/opt/axion/tenants/<slug>/
  data/
    config.json
    workspace/
  tenant.env
  docker-compose.yml
```

Cada tenant usa:

- um container `PicoClaw`
- um `workspace` persistente próprio
- um hostname dedicado
- limites de leitura e escrita apontando só para o próprio workspace
- rede `axion_tenants` para exposição via `Traefik`
- rede `axion_internal` para falar com serviços internos futuros

## Segurança

- WAF e bot protection esperados na borda do `Cloudflare`
- host hardening via `ufw` + `fail2ban`
- `docker-socket-proxy` no lugar de expor o socket Docker bruto ao Traefik
- sem mount de docker socket dentro dos tenants
- deny patterns em `exec` para bloquear comandos destrutivos
- `restrict_to_workspace=true`

## Reprovisionamento

O caminho rápido de restauração é:

1. bootstrap do host
2. clone do repo
3. restauração do `.env`
4. `compose-up`
5. restore `restic`
6. `provision-picoclaw-tenant.sh` para tenants novos ou restore dos diretórios existentes

Com imagens já presentes no host, a plataforma base + um tenant novo ficam prontos em menos de 1 minuto na prática.
