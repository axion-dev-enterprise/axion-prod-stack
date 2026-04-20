# Deploy Guide

1. Copie `env/.env.example` para `.env` e preencha as variáveis.
2. Ajuste `BASE_DOMAIN`, `CF_TUNNEL_TOKEN`, chaves OpenRouter e R2.
3. Suba com:
```bash
./scripts/deploy/compose-up.sh
```
4. Teste:
```bash
./scripts/smoke/smoke-http.sh https://router.seudominio.com
```
5. Configure backup:
```bash
./scripts/r2/rclone-config-r2.sh
./scripts/backup/backup-configs.sh
./scripts/r2/r2-sync-push.sh
```
