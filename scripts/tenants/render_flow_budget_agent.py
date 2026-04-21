#!/usr/bin/env python3
import json
import os
import stat
import sys
import textwrap
from pathlib import Path


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: render_flow_budget_agent.py <tenant-slug> <tenant-host> <data-dir> <scan-host>",
            file=sys.stderr,
        )
        return 1

    tenant_slug = sys.argv[1]
    tenant_host = sys.argv[2]
    data_dir = Path(sys.argv[3])
    scan_host = sys.argv[4]
    budget_server_url = env("FLOW_BUDGET_SERVER_URL", "http://187.77.58.53:3456/gerar-orcamento")
    budget_method = env("FLOW_BUDGET_SERVER_METHOD", "POST").upper()
    download_field = env("FLOW_BUDGET_SERVER_DOWNLOAD_FIELD", "pdf_url")
    fallback_fields = env("FLOW_BUDGET_SERVER_FALLBACK_FIELDS", "url,download_url,pdf")
    assistant_name = env("FLOW_BUDGET_ASSISTANT_NAME", "Ana")
    provider = env("FLOW_LLM_PROVIDER", "openrouter").strip().lower()
    model_name = env("PICOCLAW_DEFAULT_MODEL", "openrouter/free")
    upstream_model = env("PICOCLAW_UPSTREAM_MODEL", model_name)
    api_base = env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = env("OPENROUTER_API_KEY")

    if provider == "cloudflare":
        cf_account_id = env("CF_ACCOUNT_ID")
        api_base = env(
            "CF_WORKERS_AI_BASE_URL",
            f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id}/ai/v1" if cf_account_id else "",
        )
        model_name = env("PICOCLAW_DEFAULT_MODEL", "cloudflare/llama")
        upstream_model = env("PICOCLAW_UPSTREAM_MODEL", "openai/@cf/meta/llama-3.1-8b-instruct")
        api_key = env("CF_API_TOKEN")

    config = {
        "version": 3,
        "agents": {
            "defaults": {
                "model_name": model_name,
                "workspace": "/root/.picoclaw/workspace",
                "restrict_to_workspace": True,
                "max_tokens": int(env("PICOCLAW_DEFAULT_MAX_TOKENS", "4096")),
                "context_window": int(env("PICOCLAW_DEFAULT_CONTEXT_WINDOW", "131072")),
                "temperature": 0.2,
                "max_tool_iterations": 6,
                "summarize_message_threshold": 12,
                "summarize_token_percent": 60,
                "tool_feedback": {
                    "enabled": env("PICOCLAW_TOOL_FEEDBACK", "true").lower() == "true",
                    "max_args_length": 240,
                },
            }
        },
        "model_list": [
            {
                "model_name": model_name,
                "model": upstream_model,
                "api_base": api_base,
                "api_keys": [api_key] if api_key else [],
                "enabled": True,
            }
        ],
        "tools": {
            "allow_read_paths": ["/root/.picoclaw/workspace"],
            "allow_write_paths": ["/root/.picoclaw/workspace"],
            "exec": {
                "enabled": True,
                "enable_deny_patterns": True,
                "custom_deny_patterns": [
                    "rm -rf /",
                    "shutdown",
                    "reboot",
                    "poweroff",
                    "docker ",
                    "docker-compose",
                    "iptables",
                    "ufw ",
                    "mount ",
                    "umount ",
                    "dd if=",
                ],
                "custom_allow_patterns": [
                    "ls",
                    "pwd",
                    "cat",
                    "sed",
                    "awk",
                    "grep",
                    "rg",
                    "find",
                    "python",
                    "python3",
                    "node",
                    "npm",
                    "pnpm",
                    "git",
                    "curl",
                    "wget",
                    "bash",
                    "sh",
                    "/root/.picoclaw/workspace/tools/send_budget_request.sh",
                    "/root/.picoclaw/workspace/tools/cf_embed_text.sh",
                ],
            },
            "append_file": {"enabled": True},
            "edit_file": {"enabled": False},
            "find_skills": {"enabled": False},
            "install_skill": {"enabled": False},
            "list_dir": {"enabled": True},
            "message": {"enabled": False},
            "read_file": {"enabled": True, "mode": "bytes"},
            "spawn": {"enabled": False},
            "subagent": {"enabled": False},
            "web_fetch": {"enabled": False},
            "write_file": {"enabled": True},
        },
        "channel_list": {
            "whatsapp": {
                "enabled": True,
                "type": "whatsapp_native",
                "settings": {
                    "use_native": True,
                    "session_store_path": "/root/.picoclaw/whatsapp_session",
                },
            },
            "pico": {
                "enabled": True,
                "type": "pico",
                "settings": {
                    "token": env("TENANT_ADMIN_TOKEN"),
                    "allow_origins": [
                        f"https://{tenant_host}",
                        scan_host,
                    ],
                },
            },
        },
        "gateway": {
            "host": "0.0.0.0",
            "port": int(env("PICOCLAW_GATEWAY_PORT", "18790")),
            "hot_reload": False,
            "log_level": "info",
        },
        "heartbeat": {
            "enabled": False,
        },
        "hooks": {
            "enabled": True,
            "defaults": {
                "observer_timeout_ms": 500,
                "interceptor_timeout_ms": 5000,
                "approval_timeout_ms": 60000,
            },
            "processes": {
                "flow_tool_hook": {
                    "enabled": True,
                    "priority": 10,
                    "transport": "stdio",
                    "command": [
                        "python3",
                        "/root/.picoclaw/workspace/hooks/flow_tool_hook.py",
                    ],
                    "intercept": ["before_llm", "before_tool"],
                    "env": {
                        "FLOW_BUDGET_SCRIPT": "/root/.picoclaw/workspace/tools/send_budget_request.sh",
                        "FLOW_MEMORY_PATH": f"/root/.picoclaw/workspace/memory/{tenant_slug}-latest-intake.md",
                    },
                }
            },
        },
    }

    data_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir = data_dir / "workspace"
    tools_dir = workspace_dir / "tools"
    runtime_dir = workspace_dir / "runtime"
    outgoing_dir = workspace_dir / "outgoing"
    notes_dir = workspace_dir / "memory"
    flow_skill_dir = workspace_dir / "skills" / "flow"
    hooks_dir = workspace_dir / "hooks"
    for directory in [workspace_dir, tools_dir, runtime_dir, outgoing_dir, notes_dir, flow_skill_dir, hooks_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    (data_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    write_text(
        workspace_dir / "BOOTSTRAP.md",
        f"""
        # FLOW Budget Assistant Bootstrap

        Identidade atual: `{assistant_name}`.
        Tenant atual: `{tenant_slug}`.
        Host atual: `{tenant_host}`.

        Objetivo:
        - atender clientes no WhatsApp com rapidez;
        - coletar apenas os dados minimos para orcamento;
        - acionar o servidor de orcamentos em `{budget_server_url}`;
        - devolver ao cliente um link do PDF, ou o caminho do PDF gerado, sem enrolacao.

        Fluxo obrigatorio:
        1. Cumprimente de forma curta e objetiva.
        2. Colete nome, telefone, empresa ou loja, cidade, itens desejados, medidas ou quantidades e urgencia.
        3. Registre um resumo curto em `memory/{tenant_slug}-latest-intake.md`.
        4. Monte um JSON de orcamento e envie com `tools/send_budget_request.sh`.
        5. Se houver `pdf_url`, responda com o link.
        6. Se houver PDF local gerado, informe o caminho ou o link correto.

        Payload preferencial:
        - `empresa`
        - `cnpj`
        - `contato`
        - `telefone`
        - `configuracao_texto`
        - `capacidade`
        - `niveis`

        Regras:
        - nao invente preco;
        - nao invente prazo;
        - nao invente contato, e-mail, endereco ou assinatura;
        - nao diga que o orcamento foi enviado antes do servidor responder;
        - se faltar medida, quantidade ou item, pergunte antes de solicitar o orcamento;
        - prefira perguntas curtas, uma por vez;
        - em `cli`, responda em texto simples para o operador;
        - em `cli`, nunca tente usar `message`, `telegram`, `whatsapp` ou qualquer envio externo;
        - antes de falar em PDF, use `tools/send_budget_request.sh` e baseie a resposta apenas no retorno real do servidor.
        """,
    )

    write_text(
        workspace_dir / "SOUL.md",
        f"""
        # SOUL

        - Seu nome operacional e `{assistant_name}`.
        - Voce atende como comercial do FLOW com agilidade, clareza e pouca firula.
        - Respostas curtas por padrao.
        - Seja prestativa e segura, sem soar robotica.
        - Nao abra com "otima pergunta" ou formulas corporativas.
        - Se o cliente quer orcamento, conduza a conversa para os dados minimos e avance.
        - Nao chute prazo, preco, estoque ou frete.
        - Se algo estiver faltando, diga exatamente o que falta.
        - Nao use listas gigantes, contatos falsos, assinaturas falsas ou dados inventados.
        - Se o canal for `cli`, trate o interlocutor como operador interno.
        """,
    )

    write_text(
        workspace_dir / "MEMORY.md",
        f"""
        # MEMORY

        ## Contexto estavel

        - Assistente: `{assistant_name}`
        - Tenant: `{tenant_slug}`
        - Host publico: `{tenant_host}`
        - Scanner publico: `{scan_host}`
        - Servidor de orcamentos: `{budget_server_url}`
        - Provider LLM atual: `{provider}`
        - Modelo atual: `{upstream_model}`
        - Metodo padrao do servidor: `{budget_method}`
        - Campo principal esperado para retorno: `{download_field}`
        - Campos alternativos aceitos: `{fallback_fields}`

        ## Dados minimos para orcamento

        - nome do cliente
        - telefone
        - empresa ou loja
        - cidade
        - itens desejados
        - medidas ou quantidades
        - observacoes relevantes

        ## Observacoes operacionais

        - O alvo principal e gerar orcamento com QR facil e onboarding rapido no WhatsApp.
        - O servidor de orcamentos pode retornar URL do PDF ou o proprio PDF em base64.
        - Sempre registrar um resumo curto da coleta no workspace antes de acionar o orcamento.
        - Em testes `cli`, a saida deve ser texto curto para o operador.
        - Em testes `cli`, nunca chamar `message`, `telegram` ou qualquer envio externo.
        - So existe orcamento valido quando `send_budget_request.sh` retornar sucesso.
        - Se o servidor ainda nao foi chamado, diga que faltam dados ou que o orcamento ainda nao foi gerado.
        """,
    )

    write_text(
        workspace_dir / "tools" / "README.md",
        """
        # Tools

        - `send_budget_request.sh`: envia um payload JSON ao servidor de orcamentos e tenta extrair `pdf_url`, `download_url` ou um PDF local.
        - `cf_embed_text.sh`: gera embeddings no Workers AI da Cloudflare para memoria semantica e recuperacao futura.
        """,
    )

    write_text(
        flow_skill_dir / "SKILL.md",
        textwrap.dedent(
            f"""\
            ---
            name: flow
            description: Atende pedidos de orcamento do FLOW, coleta dados minimos e usa send_budget_request.sh para obter pdf_url real.
            ---

            # FLOW Skill

            Use este skill quando o pedido envolver orcamento, PDF, proposta comercial ou gondolas.

            Fluxo:
            1. Se faltarem dados minimos, faca uma pergunta curta por vez.
            2. Grave um resumo curto em `memory/{tenant_slug}-latest-intake.md`.
            3. Monte um JSON enxuto com `empresa`, `contato`, `telefone`, `configuracao_texto`, `capacidade` e `niveis` quando houver.
            4. Execute `sh /root/.picoclaw/workspace/tools/send_budget_request.sh <arquivo-json>`.
            5. So responda com PDF ou URL se o retorno do script trouxer sucesso real.

            Regras:
            - Nunca use `message`, `reaction`, `subagent`, `find_skills` ou envio externo em `cli`.
            - Nunca tente editar este skill durante a conversa.
            - Nunca invente `pdf_url`, preco, prazo ou assinatura.
            - Se o script falhar, responda curto explicando o erro real.
            - Em `cli`, a resposta final deve ser texto simples para o operador.
            """
        ),
    )

    flow_hook = textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import json
        import os
        import subprocess
        import sys
        import tempfile


        BUDGET_SCRIPT = os.environ.get("FLOW_BUDGET_SCRIPT", "/root/.picoclaw/workspace/tools/send_budget_request.sh")
        MEMORY_PATH = os.environ.get("FLOW_MEMORY_PATH", "/root/.picoclaw/workspace/memory/{tenant_slug}-latest-intake.md")


        def respond(msg_id, result):
            payload = {{"jsonrpc": "2.0", "id": msg_id, "result": result}}
            sys.stdout.write(json.dumps(payload) + "\\n")
            sys.stdout.flush()


        def normalize_capacidade(raw_value):
            text = str(raw_value or "").strip().lower()
            if "500" in text:
                return "500kg"
            if "250" in text:
                return "250kg"
            return "200kg"


        def normalize_niveis(raw_value):
            text = str(raw_value or "").strip().lower()
            for level in [6, 5, 4, 3]:
                if str(level) in text:
                    return level
            return 4


        def build_payload(args):
            nome = str(args.get("nome", "")).strip()
            telefone = str(args.get("telefone", "")).strip()
            loja = str(args.get("loja", "")).strip()
            cidade = str(args.get("cidade", "")).strip()
            gondola = str(args.get("gondola", "")).strip()
            preco = str(args.get("preco", "")).strip()
            capacidade = normalize_capacidade(args.get("capacidade", "") or preco)
            niveis = normalize_niveis(args.get("niveis", "") or preco)
            configuracao = " | ".join(
                part for part in [
                    f"cliente: {{nome}}" if nome else "",
                    f"loja: {{loja}}" if loja else "",
                    f"cidade: {{cidade}}" if cidade else "",
                    f"telefone: {{telefone}}" if telefone else "",
                    f"medidas: {{gondola}}" if gondola else "",
                    f"linha: {{preco}}" if preco else "",
                    f"capacidade: {{capacidade}}" if capacidade else "",
                    f"niveis: {{niveis}}" if niveis else "",
                ] if part
            )
            return {{
                "empresa": loja or nome or "Cliente FLOW",
                "contato": nome or loja or "Cliente FLOW",
                "telefone": telefone,
                "configuracao_texto": configuracao,
                "capacidade": capacidade,
                "niveis": niveis,
            }}


        def save_memory(args):
            os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
            lines = [
                f"nome: {{args.get('nome', '')}}",
                f"telefone: {{args.get('telefone', '')}}",
                f"loja: {{args.get('loja', '')}}",
                f"cidade: {{args.get('cidade', '')}}",
                f"gondola: {{args.get('gondola', '')}}",
                f"preco: {{args.get('preco', '')}}",
                f"capacidade: {{normalize_capacidade(args.get('capacidade', '') or args.get('preco', ''))}}",
                f"niveis: {{normalize_niveis(args.get('niveis', '') or args.get('preco', ''))}}",
            ]
            with open(MEMORY_PATH, "w", encoding="utf-8") as fh:
                fh.write("\\n".join(lines).strip() + "\\n")


        def handle_before_llm(msg_id, params):
            tools = list(params.get("tools", []))
            tools.append(
                {{
                    "type": "function",
                    "function": {{
                        "name": "flow",
                        "description": "Gerar orcamento FLOW com dados do cliente e retornar pdf_url real ou caminho do PDF.",
                        "parameters": {{
                            "type": "object",
                            "properties": {{
                                "nome": {{"type": "string", "description": "Nome do cliente"}},
                                "telefone": {{"type": "string", "description": "Telefone do cliente"}},
                                "loja": {{"type": "string", "description": "Empresa, loja ou mercado"}},
                                "cidade": {{"type": "string", "description": "Cidade do cliente"}},
                                "gondola": {{"type": "string", "description": "Medidas, quantidades ou configuracao principal"}},
                                "preco": {{"type": "string", "description": "Observacao comercial, linha, premium, plus ou detalhe do pedido"}},
                                "capacidade": {{"type": "string", "description": "Capacidade da gondola: 200kg, 250kg ou 500kg"}},
                                "niveis": {{"type": "string", "description": "Quantidade de niveis, preferencialmente 3, 4, 5 ou 6"}},
                            }},
                            "required": ["nome", "telefone", "loja", "cidade", "gondola"],
                        }},
                    }},
                }}
            )
            respond(
                msg_id,
                {{
                    "action": "modify",
                    "request": {{
                        "model": params.get("model"),
                        "messages": params.get("messages", []),
                        "tools": tools,
                        "options": params.get("options", {{}}),
                    }},
                }},
            )


        def handle_flow(msg_id, params):
            args = params.get("arguments", {{}})
            save_memory(args)
            payload = build_payload(args)
            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".json") as tmp:
                json.dump(payload, tmp, ensure_ascii=False)
                tmp_path = tmp.name
            try:
                proc = subprocess.run(
                    ["sh", BUDGET_SCRIPT, tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=45,
                    check=False,
                )
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

            stdout = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            if proc.returncode == 0 and stdout:
                llm_result = stdout
                user_result = "Orcamento gerado com sucesso."
                try:
                    parsed = json.loads(stdout)
                    pdf_url = parsed.get("url") or parsed.get("pdf_url")
                    file_path = parsed.get("file_path")
                    delivery_mode = parsed.get("delivery_mode", "")
                    if pdf_url:
                        llm_result = (
                            "Orcamento gerado com sucesso. "
                            f"Entrega: {{delivery_mode or 'url'}}. "
                            f"pdf_url: {{pdf_url}}. "
                            "Responda em portugues, de forma curta, confirmando o orcamento e enviando somente esse link."
                        )
                        user_result = f"Orcamento gerado com sucesso. PDF: {{pdf_url}}"
                    elif file_path:
                        llm_result = (
                            "Orcamento gerado com sucesso. "
                            f"Arquivo salvo em: {{file_path}}. "
                            "Responda em portugues, de forma curta, confirmando que o PDF foi gerado e indicando esse caminho."
                        )
                        user_result = f"Orcamento gerado com sucesso. Arquivo PDF: {{file_path}}"
                    else:
                        llm_result = (
                            "O servidor retornou sucesso, mas sem link direto. "
                            f"Resposta bruta: {{stdout}}. "
                            "Responda em portugues, de forma curta, explicando o estado real."
                        )
                        user_result = f"Orcamento gerado. Retorno do servidor: {{stdout}}"
                except Exception:
                    pass
                respond(
                    msg_id,
                    {{
                        "action": "respond",
                        "call": {{
                            "tool": "flow",
                            "arguments": args,
                        }},
                        "result": {{
                            "for_llm": llm_result,
                            "for_user": user_result,
                            "silent": False,
                            "is_error": False,
                            "response_handled": True,
                        }},
                    }},
                )
                return

            respond(
                msg_id,
                {{
                    "action": "respond",
                    "call": {{
                        "tool": "flow",
                        "arguments": args,
                    }},
                    "result": {{
                        "for_llm": stderr or stdout or "budget request failed",
                        "for_user": "",
                        "silent": False,
                        "is_error": True,
                    }},
                }},
            )


        def main():
            for raw in sys.stdin:
                line = raw.strip()
                if not line:
                    continue
                msg = json.loads(line)
                method = msg.get("method")
                msg_id = msg.get("id")
                params = msg.get("params", {{}})

                if method == "hook.hello":
                    respond(msg_id, {{"ok": True, "name": "flow_tool_hook"}})
                    continue

                if method == "hook.before_llm":
                    handle_before_llm(msg_id, params)
                    continue

                if method == "hook.before_tool" and params.get("tool") == "flow":
                    handle_flow(msg_id, params)
                    continue

                respond(msg_id, {{"action": "continue"}})


        if __name__ == "__main__":
            main()
        """
    )
    flow_hook_path = hooks_dir / "flow_tool_hook.py"
    flow_hook_path.write_text(flow_hook, encoding="utf-8")
    flow_hook_path.chmod(flow_hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    budget_script = textwrap.dedent(
        f"""\
        #!/bin/sh
        set -eu

        BUDGET_URL="{budget_server_url}"
        BUDGET_METHOD="{budget_method}"
        TOKEN_HEADER="{env("FLOW_BUDGET_SERVER_TOKEN_HEADER", "Authorization")}"
        TOKEN_VALUE="{env("FLOW_BUDGET_SERVER_TOKEN", "")}"
        HOST_HEADER="{env("FLOW_BUDGET_SERVER_HOST_HEADER", "")}"
        PRIMARY_FIELD="{download_field}"
        FALLBACK_FIELDS="{fallback_fields}"
        OUT_DIR="/root/.picoclaw/workspace/outgoing"
        RUNTIME_DIR="/root/.picoclaw/workspace/runtime"

        mkdir -p "$OUT_DIR" "$RUNTIME_DIR"

        if [ "$#" -gt 0 ]; then
          PAYLOAD="$(cat "$1")"
        else
          PAYLOAD="$(cat)"
        fi

        if [ -z "$PAYLOAD" ]; then
          echo "payload required" >&2
          exit 1
        fi

        AUTH_HEADER=""
        HOST_HEADER_ARG=""
        if [ -n "$TOKEN_VALUE" ]; then
          AUTH_HEADER="$TOKEN_HEADER: $TOKEN_VALUE"
        fi
        if [ -n "$HOST_HEADER" ]; then
          HOST_HEADER_ARG="Host: $HOST_HEADER"
        fi

        RESPONSE_FILE="$RUNTIME_DIR/last_budget_response.json"
        PAYLOAD_FILE="$(mktemp)"
        trap 'rm -f "$PAYLOAD_FILE"' EXIT
        printf '%s' "$PAYLOAD" > "$PAYLOAD_FILE"

        set -- \
          --timeout=45 \
          --tries=1 \
          "--header=Content-Type: application/json" \
          "--method=$BUDGET_METHOD" \
          "--body-file=$PAYLOAD_FILE" \
          -O "$RESPONSE_FILE"
        if [ -n "$AUTH_HEADER" ]; then
          set -- "$@" "--header=$AUTH_HEADER"
        fi
        if [ -n "$HOST_HEADER_ARG" ]; then
          set -- "$@" "--header=$HOST_HEADER_ARG"
        fi

        wget -q "$@" "$BUDGET_URL"

        RESPONSE_JSON="$(tr -d '\\r\\n' < "$RESPONSE_FILE")"
        URL_FIELDS="$PRIMARY_FIELD,$FALLBACK_FIELDS"

        extract_json_field() {{
          field_name="$1"
          printf '%s' "$RESPONSE_JSON" | sed -n "s/.*\\\"$field_name\\\":\\\"\\([^\\\"]*\\)\\\".*/\\1/p"
        }}

        OLD_IFS="$IFS"
        IFS=','
        for field in $URL_FIELDS; do
          if [ -n "$field" ]; then
            value="$(extract_json_field "$field")"
            if printf '%s' "$value" | grep -q '^http'; then
              printf '{{"status":"ok","delivery_mode":"url","url":"%s"}}\n' "$value"
              exit 0
            fi
          fi
        done
        IFS="$OLD_IFS"

        for field in pdf_base64 file_base64 document_base64; do
          value="$(extract_json_field "$field")"
          if [ -n "$value" ]; then
            value="${{value#data:application/pdf;base64,}}"
            target="$OUT_DIR/budget-$(date +%s).pdf"
            printf '%s' "$value" | base64 -d > "$target"
            printf '{{"status":"ok","delivery_mode":"file","file_path":"%s"}}\n' "$target"
            exit 0
          fi
        done

        printf '{{"status":"ok","delivery_mode":"raw","response_file":"%s"}}\n' "$RESPONSE_FILE"
        """
    )
    budget_script_path = tools_dir / "send_budget_request.sh"
    budget_script_path.write_text(budget_script, encoding="utf-8")
    budget_script_path.chmod(budget_script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    embed_script = textwrap.dedent(
        f"""\
        #!/bin/sh
        set -eu

        CF_ACCOUNT_ID="{env("CF_ACCOUNT_ID")}"
        CF_API_TOKEN="{env("CF_API_TOKEN")}"
        CF_EMBED_MODEL="{env("CF_EMBED_MODEL", "@cf/baai/bge-m3")}"

        if [ -z "$CF_ACCOUNT_ID" ] || [ -z "$CF_API_TOKEN" ]; then
          echo "cloudflare embedding vars missing" >&2
          exit 1
        fi

        if [ "$#" -gt 0 ]; then
          INPUT_TEXT="$*"
        else
          INPUT_TEXT="$(cat)"
        fi

        if [ -z "$INPUT_TEXT" ]; then
          echo "text required" >&2
          exit 1
        fi

        PAYLOAD_FILE="$(mktemp)"
        trap 'rm -f "$PAYLOAD_FILE"' EXIT
        printf '{{"text":["%s"]}}' "$(printf '%s' "$INPUT_TEXT" | sed 's/"/\\"/g')" > "$PAYLOAD_FILE"

        wget -qO- \
          --header="Authorization: Bearer $CF_API_TOKEN" \
          --header="Content-Type: application/json" \
          --post-file="$PAYLOAD_FILE" \
          "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/ai/run/$CF_EMBED_MODEL"
        """
    )
    embed_script_path = tools_dir / "cf_embed_text.sh"
    embed_script_path.write_text(embed_script, encoding="utf-8")
    embed_script_path.chmod(embed_script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    write_text(
        workspace_dir / "HEARTBEAT.md",
        """
        # HEARTBEAT

        Nenhuma tarefa automatica configurada para este tenant.
        """,
    )

    write_text(
        workspace_dir / "runtime" / ".gitkeep",
        "",
    )
    write_text(
        workspace_dir / "outgoing" / ".gitkeep",
        "",
    )
    write_text(
        workspace_dir / "memory" / ".gitkeep",
        "",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
