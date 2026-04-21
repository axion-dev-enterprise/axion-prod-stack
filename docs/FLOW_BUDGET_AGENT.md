# FLOW Budget Agent

Provisionamento enxuto para o novo sistema FLOW:

- PicoClaw com `whatsapp_native`
- QR facil pelo scanner existente
- workspace bootstrapado com `BOOTSTRAP.md`, `SOUL.md` e `MEMORY.md`
- script local para acionar servidor de orcamentos

## Objetivo

Criar um agente comercial focado em:

- coleta curta de dados basicos
- pedido de orcamento
- retorno de `pdf_url` ou arquivo PDF gerado

## Uso

```bash
./scripts/tenants/provision-flow-budget-agent.sh gondolas
```

Ou com host explicito:

```bash
./scripts/tenants/provision-flow-budget-agent.sh gondolas bot.gondolas.axionenterprise.cloud
```

## Variaveis relevantes

- `FLOW_BUDGET_SERVER_URL`
- `FLOW_BUDGET_SERVER_METHOD`
- `FLOW_BUDGET_SERVER_TOKEN`
- `FLOW_BUDGET_SERVER_TOKEN_HEADER`
- `FLOW_BUDGET_SERVER_HOST_HEADER`
- `FLOW_BUDGET_SERVER_DOWNLOAD_FIELD`
- `FLOW_BUDGET_SERVER_FALLBACK_FIELDS`
- `FLOW_BUDGET_ASSISTANT_NAME`
- `FLOW_BUDGET_SCAN_ORIGIN`

## Observacao importante

No ambiente local atual, `ana.gondolasmaringa.com.br` nao resolveu por DNS durante a validacao. O provisionamento ja deixa o endpoint parametrizado, mas o contrato real do servidor de orcamentos ainda precisa ser validado no host de destino ou com DNS funcional.
