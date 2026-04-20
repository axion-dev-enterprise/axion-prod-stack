# Monitoring, Logs And Alerts

## Observabilidade padrão

- `Alloy` coleta logs dos containers
- `Loki` armazena logs
- `Grafana` visualiza logs e métricas
- `Uptime Kuma` faz smoke checks e health checks externos

## Alertas

Os scripts já preveem:

- `HEALTHCHECKS_PING_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `SLACK_WEBHOOK_URL`

## Checks sugeridos

- plataforma base
- `grafana`
- `status`
- cada hostname de tenant provisionado
- health do Postgres
- health do Valkey
- health do NATS
