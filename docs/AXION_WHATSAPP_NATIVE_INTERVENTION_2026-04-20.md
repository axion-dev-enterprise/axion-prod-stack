# AXION WhatsApp Native Intervention

Data da intervencao: `2026-04-20`

## Objetivo

Restaurar a integracao nativa do WhatsApp no PicoClaw V3 e corrigir falhas de inicializacao do bot.

## Diagnostico

- O binario nativo em `/bin/picoclaw` falhava com `model "" not found in model_list`.
- O `config.json` presente no ambiente estava em formato legado ou misto e nao atendia ao esquema exigido pelo PicoClaw V3.
- O canal de WhatsApp estava configurado de forma ambigua com `type: whatsapp` e `use_native: true`, mas a logica atual exige `type: whatsapp_native`.

## Descobertas tecnicas

- O modelo padrao agora precisa estar em `agents.defaults.model_name`.
- Canais do tipo `pico` exigem `token` nao vazio.
- O canal nativo de WhatsApp deve ser declarado explicitamente como `whatsapp_native`.
- A persistencia de sessao do WhatsApp foi configurada em `/root/.picoclaw/whatsapp_session`.

## Intervencoes executadas

- Analise do codigo fonte em `pkg/config/` no servidor para confirmar os campos obrigatorios da `Config` V3.
- Geracao de novo `config.json` em formato limpo, enviado via Base64 para evitar problemas de escape no shell remoto.
- Ajuste da configuracao para `version: 3`.
- Saneamento de instancias orfas em Docker.
- Recriacao do container `picoclaw-axion-official` com mounts e labels de rede corretos.
- Validacao de inicializacao bem-sucedida de `Cron`, `Heartbeat` e `Channel Manager`.
- Confirmacao de 2 canais habilitados: `pico` e `whatsapp`.

## Resultado operacional

- Gateway nativo online na porta `18790`.
- Modulo `whatsmeow` inicializado com sucesso.
- QR de autenticacao disponibilizado para o scanner em `scan.axionenterprise.cloud`.

## Configuracao de referencia

```json
{
  "version": 3,
  "agents": {
    "defaults": {
      "model_name": "openrouter/xiaomi/mimo-v2-pro"
    }
  },
  "channel_list": {
    "whatsapp": {
      "enabled": true,
      "type": "whatsapp_native",
      "settings": {
        "use_native": true,
        "session_store_path": "/root/.picoclaw/whatsapp_session"
      }
    },
    "pico": {
      "enabled": true,
      "type": "pico",
      "settings": {
        "token": "axion_default_token",
        "allow_origins": [
          "*"
        ]
      }
    }
  },
  "model_list": [
    {
      "model_name": "openrouter/xiaomi/mimo-v2-pro",
      "model": "openai/xiaomi/mimo-v2-pro",
      "enabled": true
    }
  ]
}
```

## Impacto na leitura atual do ambiente

- Explica a presenca de um fluxo operacional fora do modelo inicial de tenants `core/sales/support`.
- Explica a existencia do `qr-scanner` e do host `scan.axionenterprise.cloud`.
- Indica que parte da operacao real passou a depender de uma configuracao nativa do PicoClaw V3 aplicada diretamente no servidor.
- Mostra que hoje existe drift entre o estado do repo e o estado operacional efetivo do host.
