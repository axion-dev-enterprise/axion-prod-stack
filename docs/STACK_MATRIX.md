# Stack Matrix

| Camada | Tecnologia | Papel |
|---|---|---|
| Edge | Traefik | roteamento HTTP interno |
| WAF | Cloudflare | borda pública, WAF e access |
| Firewall | UFW + Fail2ban | proteção do host |
| Cache | Valkey | cache, locks, coordenação |
| Queue | NATS JetStream | jobs, eventos, fila |
| Metadata | Postgres + pgvector | dados da plataforma e extensões |
| Tenant runtime | PicoClaw | chatbot por cliente |
| Logs | Alloy + Loki | coleta e retenção |
| Dashboards | Grafana | visualização operacional |
| Smoke | Uptime Kuma | health e disponibilidade |
| Backup offsite | Restic + R2 | backup criptografado |
| Backup code/config | Git bundle + GitHub | recuperação rápida |
