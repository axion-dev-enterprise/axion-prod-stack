# Domain And Service Map

Leitura ao vivo feita em 20 de abril de 2026:

- `axionenterprise.cloud`
- `www.axionenterprise.cloud`
- `flow.axionenterprise.cloud`
- `sales.flow.axionenterprise.cloud`
- `support.flow.axionenterprise.cloud`
- `status.axionenterprise.cloud`
- `grafana.axionenterprise.cloud`
- `scan.axionenterprise.cloud`
- `api.axionenterprise.cloud`
- `admin.axionenterprise.cloud`

Todos esses hosts estavam resolvendo em Cloudflare no momento da leitura.

## Alocacao alvo

- `axionenterprise.cloud`: landing institucional AXION
- `www.axionenterprise.cloud`: alias da landing
- `flow.axionenterprise.cloud`: app principal FLOW
- `core.flow.axionenterprise.cloud`: tenant PicoClaw base
- `sales.flow.axionenterprise.cloud`: tenant comercial
- `support.flow.axionenterprise.cloud`: tenant suporte
- `status.axionenterprise.cloud`: Uptime Kuma e status publico/privado
- `grafana.axionenterprise.cloud`: Grafana
- `scan.axionenterprise.cloud`: scanner/bridge visual para QR do WhatsApp nativo
- `api.axionenterprise.cloud`: API AXION/FLOW e webhooks
- `admin.axionenterprise.cloud`: painel administrativo consolidado

## Hosts sem DNS publico

- `mysql`
- `postgres`
- `valkey`
- `nats`
- `n8n`
- `loki`
- `alloy`

## Regras

- Somente `80/443` ficam expostos para o origin.
- Painel e observabilidade passam por Cloudflare proxied.
- Bancos, filas e cache ficam internos ou via tunel administrativo.

## Cobertura Do Status

`https://status.axionenterprise.cloud/` foi estruturado para cobrir:

- experiencia publica: `axionenterprise.cloud`, `www`, `flow`
- billing: `axionpay`, `pay`
- control plane: `dev`, `api`, `admin`
- tenants FLOW: `core.flow`, `sales.flow`, `support.flow`
- observabilidade: `status`, `grafana`, `scan`
- servicos de base: `postgres`, `valkey`, `nats`, `loki`, `picoclaw-official`
- legados e automacao: `n8n`, `mysql`, `redis`

`/dashboard` permanece reservado para a operacao interna do Uptime Kuma.
