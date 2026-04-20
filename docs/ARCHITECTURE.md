# Arquitetura

Fluxo:
Cloudflare -> cloudflared -> Traefik -> serviços internos

Serviços principais:
- Traefik: reverse proxy
- cloudflared: tunnel Cloudflare
- Redis: cache/fila
- Ollama: LLM local leve
- router-python / router-node: roteadores OpenRouter/Ollama
- Uptime Kuma: uptime checks
- Loki + Alloy + Grafana: logs e dashboards
- R2 + rclone: backups

Política de LLM:
- classify: Ollama local
- rewrite: free fixed
- summarize: cheap fast
- qa: cheap main
- agent: balanced
- premium: premium
