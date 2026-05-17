# 🚑 Incidente: Flow fora do ar por loop de redirect

**Data:** 2026-05-17  
**Sistema:** `flow.axionenterprise.cloud`  
**Severidade:** Alta, site público indisponível por loop de redirects.

## ✅ Resultado

`https://flow.axionenterprise.cloud/` voltou a responder `200 OK`.

## 🔎 Evidência inicial

- DNS resolvia via Cloudflare para `flow.axionenterprise.cloud`.
- A resposta pública entrava em loop:
  - `308 Permanent Redirect`
  - `Location: https://flow.axionenterprise.cloud/`
- A origem direta na VPS `203.161.39.174` respondia `200 OK` por HTTPS.
- A origem por HTTP redirecionava corretamente para HTTPS.

## 🧠 Causa raiz

O SSL/TLS da zona `axionenterprise.cloud` estava em modo **Flexible** na Cloudflare.

Com isso, o visitante acessava HTTPS na borda, mas a Cloudflare chamava a origem por HTTP. A origem redirecionava HTTP para HTTPS, e a Cloudflare repetia o ciclo, criando o loop.

## 🛠️ Correção aplicada

Alterado o modo SSL/TLS da Cloudflare de `flexible` para `full`.

## 🧪 Validação

- `curl -I -L --max-redirs 5 https://flow.axionenterprise.cloud/` retornou `200 OK`.
- `Invoke-WebRequest https://flow.axionenterprise.cloud/` retornou `StatusCode: 200`.
- `curl https://flow.axionenterprise.cloud/health` retornou `ok: true`.

## 📌 Próximo controle preventivo

Manter `axionenterprise.cloud` em SSL/TLS `full` ou `full strict` quando a origem tiver certificado válido. Não usar `flexible` em serviços que redirecionam HTTP para HTTPS.
