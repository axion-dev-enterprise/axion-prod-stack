# Deploy Guide

## 1. Preparar o host

No servidor:

```bash
git clone https://github.com/axion-dev-enterprise/axion-prod-stack.git /opt/axion/platform
cd /opt/axion/platform
sudo ./scripts/deploy/bootstrap-server.sh /opt/axion/platform
```

## 2. Criar o arquivo de ambiente

```bash
cp env/.env.example env/.env
vim env/.env
```

Preencha pelo menos:

- `AXION_ROOT`
- `BASE_DOMAIN`
- `TENANT_BASE_DOMAIN`
- `OPENROUTER_API_KEY`
- `VALKEY_PASSWORD`
- `POSTGRES_PASSWORD`
- `GRAFANA_ADMIN_PASSWORD`
- `RESTIC_PASSWORD`
- `CF_R2_*`
- `BACKUP_GITHUB_TOKEN`

## 3. Tunar o host para 1 vCPU / 4 GB

```bash
sudo ./scripts/security/tune-host-resources.sh 4
```

Isso cria swap e aplica tuning conservador de memória/cache para reduzir picos de busy e OOM.

## 4. Subir a plataforma

```bash
./scripts/deploy/compose-up.sh
```

Por padrão, em servidor pequeno, a stack sobe sem observabilidade pesada.

- `ENABLE_OBSERVABILITY=false`
- `ENABLE_STATUS=false`

Ative depois se o host estiver estável.

## 5. Instalar timers de backup

```bash
sudo ./scripts/deploy/install-systemd-units.sh
```

## 6. Provisionar um tenant PicoClaw

```bash
./scripts/tenants/provision-picoclaw-tenant.sh cliente-a
```

Ou com hostname explícito:

```bash
./scripts/tenants/provision-picoclaw-tenant.sh cliente-a bot.cliente-a.axionenterprise.cloud
```

## 7. Reprovisionamento rápido

Quando o host já existe e você só quer alinhar com o GitHub:

```bash
./scripts/deploy/reprovision-fast.sh
```

## 8. Export e replica

Exportar o estado do host:

```bash
./scripts/export/export-host-config.sh
```

Preparar a replica self-host:

```bash
./scripts/deploy/bootstrap-secondary-restore.sh /opt/axion/platform /opt/axion-restore
```

Fazer cutover de DNS via Cloudflare:

```bash
./scripts/cloudflare/apply-dns-cutover.sh docs/cloudflare-dns-manifest.json <IP-DA-REPLICA>
```
