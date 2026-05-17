import asyncio
import hmac
import html
import json
import os
import re
import secrets
import time
from contextlib import suppress
from hashlib import sha256
from pathlib import Path
from typing import Optional

import aiohttp
import docker
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

app = FastAPI()

SITE_TITLE = os.getenv("TENANT_CHAT_SITE_TITLE", "AXION Tenant Chat")
PICO_TOKEN = os.getenv("TENANT_CHAT_PICO_TOKEN", "")
PICO_PORT = int(os.getenv("TENANT_CHAT_PICO_PORT", "18790"))
TENANT_SUFFIX = os.getenv("TENANT_CHAT_TENANT_SUFFIX", ".flow.axionenterprise.cloud")
CONTAINER_PREFIX = os.getenv("TENANT_CHAT_CONTAINER_PREFIX", "picoclaw-")
SCAN_HOST = os.getenv("TENANT_CHAT_SCAN_HOST", "https://scan.axionenterprise.cloud")
OPS_PASSWORD = os.getenv("AXION_OPS_PASSWORD", os.getenv("TENANT_ADMIN_TOKEN", ""))
SESSION_SECRET = os.getenv("AXION_OPS_SESSION_SECRET", OPS_PASSWORD or "axion-ops")
COOKIE_NAME = os.getenv("AXION_OPS_COOKIE_NAME", "axion_ops")
SESSION_TTL_SECONDS = int(os.getenv("AXION_OPS_SESSION_TTL_SECONDS", "43200"))
TENANTS_ROOT = Path(os.getenv("AXION_TENANTS_ROOT", "/opt/axion/tenants"))
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

docker_client = docker.from_env()


def normalize_slug(raw: str) -> str:
    slug = (raw or "").strip().lower()
    if not SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="tenant invalido")
    return slug


def tenant_from_host(host: str) -> Optional[str]:
    hostname = (host or "").split(":")[0].lower()
    if hostname.endswith(TENANT_SUFFIX):
        slug = hostname[: -len(TENANT_SUFFIX)]
        if slug and SLUG_RE.match(slug):
            return slug
    return None


def sign_value(value: str) -> str:
    return hmac.new(SESSION_SECRET.encode("utf-8"), value.encode("utf-8"), sha256).hexdigest()


def build_session_cookie() -> str:
    issued = str(int(time.time()))
    nonce = secrets.token_hex(8)
    payload = f"{issued}:{nonce}"
    return f"{payload}:{sign_value(payload)}"


def _is_valid_session_token(token: str) -> bool:
    if not OPS_PASSWORD:
        return True
    parts = token.split(":")
    if len(parts) != 3:
        return False
    issued, nonce, signature = parts
    payload = f"{issued}:{nonce}"
    if not hmac.compare_digest(sign_value(payload), signature):
        return False
    try:
        issued_at = int(issued)
    except ValueError:
        return False
    return (issued_at + SESSION_TTL_SECONDS) >= int(time.time())


def is_authenticated(request: Request) -> bool:
    return _is_valid_session_token(request.cookies.get(COOKIE_NAME, ""))


def is_websocket_authenticated(websocket: WebSocket) -> bool:
    return _is_valid_session_token(websocket.cookies.get(COOKIE_NAME, ""))


def require_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="unauthorized")


def login_html(next_path: str, error: str = "") -> str:
    error_block = ""
    if error:
        error_block = f'<div class="login-error">{html.escape(error)}</div>'
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>{html.escape(SITE_TITLE)} · Login</title>
      <style>
        :root {{
          color-scheme: dark;
          --bg: #05101a;
          --panel: rgba(8, 16, 28, 0.92);
          --border: rgba(255,255,255,0.08);
          --text: #edf4ff;
          --muted: #91a5bb;
          --danger: #ff8b8b;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          min-height: 100vh;
          display: grid;
          place-items: center;
          background: radial-gradient(circle at top, #163455 0%, #08121c 56%, #03070d 100%);
          color: var(--text);
          font-family: "Segoe UI", system-ui, sans-serif;
          padding: 24px;
        }}
        .card {{
          width: min(100%, 430px);
          border: 1px solid var(--border);
          border-radius: 28px;
          background: var(--panel);
          padding: 28px;
          box-shadow: 0 22px 64px rgba(0,0,0,.32);
        }}
        h1 {{ margin: 0 0 10px; font-size: 30px; }}
        p {{ margin: 0 0 18px; color: var(--muted); line-height: 1.6; }}
        .login-error {{
          margin-bottom: 14px;
          padding: 12px 14px;
          border-radius: 16px;
          background: rgba(255,107,107,.12);
          border: 1px solid rgba(255,107,107,.28);
          color: var(--danger);
        }}
        label {{ display: block; margin-bottom: 8px; font-size: 14px; color: var(--muted); }}
        input {{
          width: 100%;
          border-radius: 16px;
          border: 1px solid var(--border);
          background: rgba(255,255,255,0.04);
          color: var(--text);
          padding: 14px 16px;
          font: inherit;
          margin-bottom: 14px;
        }}
        button {{
          width: 100%;
          border: none;
          border-radius: 16px;
          padding: 14px 16px;
          font: inherit;
          font-weight: 700;
          background: linear-gradient(180deg, #6ae6ff 0%, #2cbbe8 100%);
          color: #04111a;
          cursor: pointer;
        }}
      </style>
    </head>
    <body>
      <form class="card" method="post" action="/auth/login">
        <h1>Console operacional</h1>
        <p>Entre para acessar os tenants, acompanhar sessoes, ver execucao de ferramentas e operar o onboarding por QR.</p>
        {error_block}
        <input type="hidden" name="next" value="{html.escape(next_path)}" />
        <label for="password">Senha de acesso</label>
        <input id="password" name="password" type="password" autocomplete="current-password" required />
        <button type="submit">Entrar</button>
      </form>
    </body>
    </html>
    """


def list_tenants() -> list[str]:
    tenants = []
    for container in docker_client.containers.list():
        if not container.name.startswith(CONTAINER_PREFIX):
            continue
        slug = container.name.replace(CONTAINER_PREFIX, "", 1)
        if SLUG_RE.match(slug):
            tenants.append(slug)
    return sorted(set(tenants))


def tenant_exists(slug: str) -> bool:
    try:
        docker_client.containers.get(f"{CONTAINER_PREFIX}{slug}")
        return True
    except docker.errors.NotFound:
        return False


def resolve_public_pdf_path(tenant: str, filename: str) -> Path:
    slug = normalize_slug(tenant)
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="arquivo invalido")
    candidate = TENANTS_ROOT / slug / "data" / "public" / "pdf" / safe_name
    resolved = candidate.resolve(strict=False)
    allowed_root = (TENANTS_ROOT / slug / "data" / "public" / "pdf").resolve(strict=False)
    if allowed_root not in resolved.parents:
        raise HTTPException(status_code=400, detail="arquivo invalido")
    return resolved


def build_index_html(tenants: list[str]) -> str:
    cards = []
    for slug in tenants:
        cards.append(
            f"""
            <a href="/chat/{html.escape(slug)}" class="card">
              <div class="tenant-name">{html.escape(slug)}</div>
              <div class="tenant-meta">Tenant isolado · WebSocket pico</div>
              <div class="tenant-actions">
                <span>Abrir console</span>
                <span class="pill">WS</span>
              </div>
            </a>
            """
        )
    if not cards:
        cards.append('<div class="empty">Nenhum tenant ativo encontrado.</div>')
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>{html.escape(SITE_TITLE)}</title>
      <style>
        :root {{
          color-scheme: dark;
          --bg: #071018;
          --panel: rgba(12, 22, 34, 0.78);
          --border: rgba(255,255,255,0.08);
          --text: #eef6ff;
          --muted: #8ca2b8;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: "Segoe UI", system-ui, sans-serif;
          background: radial-gradient(circle at top, #173252 0%, #071018 48%, #03070d 100%);
          color: var(--text);
        }}
        .wrap {{ max-width: 1080px; margin: 0 auto; padding: 48px 24px; }}
        .topbar {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 16px;
          margin-bottom: 22px;
        }}
        h1 {{ margin: 0 0 12px; font-size: 44px; }}
        p {{ margin: 0 0 28px; color: var(--muted); max-width: 760px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }}
        .card {{
          text-decoration: none;
          color: inherit;
          display: block;
          border: 1px solid var(--border);
          border-radius: 24px;
          padding: 24px;
          background: var(--panel);
          backdrop-filter: blur(16px);
          transition: transform .18s ease, border-color .18s ease;
        }}
        .card:hover {{ transform: translateY(-2px); border-color: rgba(63,194,255,.35); }}
        .tenant-name {{ font-size: 22px; font-weight: 700; margin-bottom: 8px; }}
        .tenant-meta {{ color: var(--muted); font-size: 14px; margin-bottom: 16px; }}
        .tenant-actions {{ display: flex; justify-content: space-between; color: var(--muted); font-size: 14px; align-items: center; }}
        .pill {{ border: 1px solid rgba(255,255,255,0.08); border-radius: 999px; padding: 4px 10px; }}
        .empty {{
          border: 1px dashed var(--border);
          border-radius: 24px;
          padding: 32px;
          color: var(--muted);
          text-align: center;
          background: rgba(255,255,255,0.02);
        }}
        .logout {{
          border: 1px solid var(--border);
          border-radius: 999px;
          background: rgba(255,255,255,0.04);
          color: var(--text);
          padding: 10px 14px;
          cursor: pointer;
        }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="topbar">
          <div>
            <h1>{html.escape(SITE_TITLE)}</h1>
            <p>Console operacional por tenant com sessao por aba, logs de evento, onboarding via QR e trilha de execucao para validar o comportamento do chatbot.</p>
          </div>
          <form method="post" action="/auth/logout">
            <button class="logout">Sair</button>
          </form>
        </div>
        <div class="grid">{''.join(cards)}</div>
      </div>
    </body>
    </html>
    """


def build_chat_html(slug: str) -> str:
    escaped_slug = html.escape(slug)
    ws_path = f"/chat/{escaped_slug}/ws"
    qr_url = f"{SCAN_HOST}/tenant/{escaped_slug}"
    tenant_health_url = f"https://{escaped_slug}{TENANT_SUFFIX}/health"
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>{html.escape(SITE_TITLE)} · {escaped_slug}</title>
      <style>
        :root {{
          color-scheme: dark;
          --bg: #06111a;
          --panel: rgba(14, 23, 34, 0.82);
          --border: rgba(255,255,255,0.08);
          --text: #ecf3ff;
          --muted: #8ea3b8;
          --assistant: #101c2b;
          --user: #1282d8;
          --shadow: rgba(0,0,0,.26);
          --accent: #4ad1ff;
          --ok: #66f2b6;
          --warn: #ffcf66;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: "Segoe UI", system-ui, sans-serif;
          background: radial-gradient(circle at top, #153353 0%, #06111a 48%, #04070d 100%);
          color: var(--text);
        }}
        .layout {{ max-width: 1320px; margin: 0 auto; padding: 28px 20px 32px; }}
        .header {{
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 20px;
        }}
        .title-block h1 {{ margin: 0 0 6px; font-size: 38px; }}
        .title-block p {{ margin: 0; color: var(--muted); }}
        .header-actions {{
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          align-items: center;
        }}
        .header-link, .header-actions button {{
          color: var(--text);
          text-decoration: none;
          border: 1px solid var(--border);
          border-radius: 999px;
          padding: 10px 14px;
          background: rgba(255,255,255,0.04);
          cursor: pointer;
        }}
        .stack {{
          display: grid;
          grid-template-columns: 1.45fr .85fr;
          gap: 18px;
        }}
        .panel {{
          border: 1px solid var(--border);
          border-radius: 28px;
          background: var(--panel);
          backdrop-filter: blur(16px);
          box-shadow: 0 12px 40px var(--shadow);
        }}
        .chat-panel {{ padding: 18px; min-height: 76vh; display: flex; flex-direction: column; }}
        .meta {{
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 6px 6px 18px;
          flex-wrap: wrap;
        }}
        .status {{
          color: var(--muted);
          font-size: 14px;
          display: flex;
          gap: 10px;
          align-items: center;
          flex-wrap: wrap;
        }}
        .badge {{
          display: inline-flex;
          align-items: center;
          gap: 8px;
          border-radius: 999px;
          border: 1px solid rgba(255,255,255,0.08);
          background: rgba(255,255,255,0.04);
          padding: 6px 10px;
        }}
        .dot {{ width: 8px; height: 8px; border-radius: 999px; background: var(--warn); box-shadow: 0 0 14px currentColor; }}
        .dot.ok {{ background: var(--ok); }}
        .messages {{
          flex: 1;
          overflow: auto;
          padding: 8px 4px 12px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }}
        .bubble {{
          max-width: min(84%, 760px);
          padding: 14px 16px;
          border-radius: 20px;
          line-height: 1.5;
          white-space: pre-wrap;
          word-break: break-word;
          border: 1px solid rgba(255,255,255,0.06);
        }}
        .assistant {{ background: var(--assistant); align-self: flex-start; }}
        .user {{ background: linear-gradient(180deg, #1998f2 0%, #1282d8 100%); align-self: flex-end; }}
        .system {{ background: rgba(255,255,255,0.04); color: var(--muted); align-self: center; text-align: center; }}
        .tool {{ background: rgba(74,209,255,0.08); color: #dff8ff; align-self: flex-start; border-color: rgba(74,209,255,0.24); }}
        .typing {{
          display: none;
          align-self: flex-start;
          color: var(--muted);
          padding: 8px 14px;
        }}
        .composer {{
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 12px;
          padding-top: 12px;
        }}
        textarea {{
          width: 100%;
          min-height: 68px;
          max-height: 220px;
          resize: vertical;
          border-radius: 18px;
          border: 1px solid var(--border);
          background: rgba(255,255,255,0.04);
          color: var(--text);
          padding: 14px 16px;
          font: inherit;
        }}
        button.send {{
          border: none;
          border-radius: 18px;
          padding: 0 18px;
          min-width: 148px;
          background: linear-gradient(180deg, #4ad1ff 0%, #24aef3 100%);
          color: #06111a;
          font-weight: 700;
          cursor: pointer;
        }}
        .side-panel {{ padding: 18px; display: flex; flex-direction: column; gap: 14px; }}
        .side-card {{
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 20px;
          padding: 16px;
          background: rgba(255,255,255,0.03);
        }}
        .side-card strong {{ display: block; margin-bottom: 10px; }}
        .muted {{ color: var(--muted); }}
        .mono {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
        .events {{
          display: grid;
          gap: 10px;
          max-height: 280px;
          overflow: auto;
        }}
        .event {{
          border-radius: 16px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.05);
          padding: 12px;
          font-size: 13px;
        }}
        .event-type {{
          font-weight: 700;
          color: #dff8ff;
          margin-bottom: 4px;
        }}
        .actions {{
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }}
        .actions a, .actions button {{
          color: var(--text);
          text-decoration: none;
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: 10px 12px;
          background: rgba(255,255,255,0.04);
          cursor: pointer;
        }}
        @media (max-width: 980px) {{
          .stack {{ grid-template-columns: 1fr; }}
          .chat-panel {{ min-height: auto; }}
        }}
      </style>
    </head>
    <body>
      <div class="layout">
        <div class="header">
          <div class="title-block">
            <h1>Console {escaped_slug}</h1>
            <p>Canal WebSocket com sessao por aba, trilha de eventos e acesso operacional protegido.</p>
          </div>
          <div class="header-actions">
            <a class="header-link" href="/chat">Todos os tenants</a>
            <form method="post" action="/auth/logout">
              <button type="submit">Sair</button>
            </form>
          </div>
        </div>
        <div class="stack">
          <section class="panel chat-panel">
            <div class="meta">
              <div class="status">
                <span class="badge"><span class="dot" id="socket-dot"></span><span id="status">Conectando...</span></span>
                <span class="badge mono" id="session-label">session: preparando</span>
                <span class="badge mono">tenant: {escaped_slug}</span>
              </div>
              <div class="actions">
                <button type="button" id="reset-session">Nova sessao</button>
              </div>
            </div>
            <div class="messages" id="messages"></div>
            <div class="typing" id="typing">PicoClaw esta digitando...</div>
            <form class="composer" id="composer">
              <textarea id="input" placeholder="Digite sua mensagem para o tenant {escaped_slug}...&#10;&#10;Exemplo para provar tool use: use a ferramenta exec e rode 'pwd'."></textarea>
              <button class="send" type="submit" id="send-button" disabled>Conectar...</button>
            </form>
          </section>
          <aside class="panel side-panel">
            <div class="side-card">
              <strong>Tenant</strong>
              <div class="muted mono">{escaped_slug}</div>
              <div class="muted" style="margin-top:10px">Sessao isolada por aba usando <span class="mono">sessionStorage</span>, evitando reaproveitamento silencioso entre operadores.</div>
            </div>
            <div class="side-card">
              <strong>Onboarding</strong>
              <div class="muted">Se o WhatsApp ainda nao estiver pareado, abra o QR isolado deste tenant.</div>
              <div class="actions" style="margin-top:12px">
                <a href="{html.escape(qr_url)}" target="_blank" rel="noreferrer">Abrir QR</a>
                <a href="{html.escape(tenant_health_url)}" target="_blank" rel="noreferrer">Health do tenant</a>
              </div>
            </div>
            <div class="side-card">
              <strong>Provas operacionais</strong>
              <div class="muted">Os eventos abaixo mostram quando ha digitacao, mensagens, erros e uso de ferramentas encaminhados pelo canal.</div>
            </div>
            <div class="side-card">
              <strong>Eventos recentes</strong>
              <div class="events" id="events"></div>
            </div>
          </aside>
        </div>
      </div>
      <script>
        const tenant = {json.dumps(slug)};
        const sessionKey = `axion-chat:${{location.host}}:${{tenant}}`;
        const storedSession = sessionStorage.getItem(sessionKey);
        const sessionId = storedSession || (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2));
        sessionStorage.setItem(sessionKey, sessionId);

        const messagesEl = document.getElementById("messages");
        const typingEl = document.getElementById("typing");
        const inputEl = document.getElementById("input");
        const statusEl = document.getElementById("status");
        const socketDotEl = document.getElementById("socket-dot");
        const sessionLabelEl = document.getElementById("session-label");
        const composerEl = document.getElementById("composer");
        const sendButtonEl = document.getElementById("send-button");
        const eventsEl = document.getElementById("events");
        sessionLabelEl.textContent = `session: ${{sessionId}}`;

        const messageMap = new Map();

        function appendBubble(kind, text, id) {{
          const bubble = document.createElement("div");
          bubble.className = `bubble ${{kind}}`;
          bubble.textContent = text;
          if (id) {{
            bubble.dataset.messageId = id;
            messageMap.set(id, bubble);
          }}
          messagesEl.appendChild(bubble);
          messagesEl.scrollTop = messagesEl.scrollHeight;
          return bubble;
        }}

        function appendEvent(type, content) {{
          const item = document.createElement("div");
          item.className = "event";
          item.innerHTML = `<div class="event-type">${{type}}</div><div class="muted">${{content}}</div>`;
          eventsEl.prepend(item);
          while (eventsEl.children.length > 12) {{
            eventsEl.removeChild(eventsEl.lastChild);
          }}
        }}

        function upsertAssistantMessage(id, text) {{
          if (id && messageMap.has(id)) {{
            messageMap.get(id).textContent = text;
            return;
          }}
          appendBubble("assistant", text, id);
        }}

        function setStatus(text, isOk) {{
          statusEl.textContent = text;
          socketDotEl.classList.toggle("ok", !!isOk);
          sendButtonEl.disabled = !isOk;
          sendButtonEl.textContent = isOk ? "Enviar" : "Conectando...";
        }}

        document.getElementById("reset-session").addEventListener("click", () => {{
          sessionStorage.removeItem(sessionKey);
          location.reload();
        }});

        const scheme = location.protocol === "https:" ? "wss" : "ws";
        const socket = new WebSocket(`${{scheme}}://${{location.host}}{ws_path}?session_id=${{encodeURIComponent(sessionId)}}`);

        socket.addEventListener("open", () => {{
          setStatus("Conectado", true);
          appendBubble("system", "Conexao WebSocket ativa com o tenant.", null);
          appendEvent("socket.open", "Canal pronto para envio de mensagens.");
        }});

        socket.addEventListener("message", (event) => {{
          try {{
            const data = JSON.parse(event.data);
            if (data.type === "session.ready") {{
              appendEvent("session.ready", `Sessao pronta: ${{data.session_id || sessionId}}`);
              return;
            }}
            if (data.type === "typing.start") {{
              typingEl.style.display = "block";
              appendEvent("typing.start", "O tenant iniciou a digitacao.");
              return;
            }}
            if (data.type === "typing.stop") {{
              typingEl.style.display = "none";
              appendEvent("typing.stop", "O tenant encerrou a digitacao.");
              return;
            }}
            if (data.type === "message.create" || data.type === "message.update") {{
              typingEl.style.display = "none";
              if (data.thought) return;
              upsertAssistantMessage(data.message_id || null, data.content || "");
              appendEvent(data.type, (data.content || "").slice(0, 140) || "Mensagem vazia.");
              return;
            }}
            if (data.type === "tool.event") {{
              const label = data.tool_name ? `${{data.tool_name}}` : "tool";
              appendBubble("tool", `Ferramenta: ${{label}}\\n${{data.summary || "atividade registrada"}}`, null);
              appendEvent("tool.event", `${{label}} · ${{data.summary || "atividade registrada"}}`);
              return;
            }}
            if (data.type === "error") {{
              appendBubble("system", `Erro: ${{data.message || "falha desconhecida"}}`, null);
              appendEvent("error", data.message || "falha desconhecida");
              return;
            }}
            appendEvent(data.type || "event", JSON.stringify(data).slice(0, 240));
          }} catch {{
            appendBubble("system", "Falha ao interpretar uma mensagem do socket.", null);
          }}
        }});

        socket.addEventListener("close", () => {{
          setStatus("Desconectado", false);
          typingEl.style.display = "none";
          appendBubble("system", "A conexao foi encerrada. Recarregue a pagina para reconectar.", null);
          appendEvent("socket.close", "Conexao encerrada.");
        }});

        socket.addEventListener("error", () => {{
          setStatus("Erro de conexao", false);
          appendEvent("socket.error", "Falha na conexao WebSocket.");
        }});

        composerEl.addEventListener("submit", (event) => {{
          event.preventDefault();
          const content = inputEl.value.trim();
          if (!content || socket.readyState !== WebSocket.OPEN) return;
          appendBubble("user", content, null);
          appendEvent("message.send", content.slice(0, 140));
          socket.send(JSON.stringify({{ type: "message.send", content }}));
          inputEl.value = "";
          inputEl.focus();
        }});
      </script>
    </body>
    </html>
    """


def tenant_html_response(slug: str) -> HTMLResponse:
    return HTMLResponse(build_chat_html(normalize_slug(slug)))


def summarize_event(event_type: str, payload: dict) -> tuple[str, str]:
    tool_name = str(payload.get("tool") or payload.get("tool_name") or payload.get("name") or "").strip()
    if not tool_name and "tool" in event_type:
        tool_name = event_type.split(".")[-1]
    summary = (
        payload.get("message")
        or payload.get("content")
        or payload.get("status")
        or payload.get("result")
        or payload.get("text")
        or ""
    )
    summary_text = str(summary).strip()
    if not summary_text:
        summary_text = f"evento {event_type}"
    return tool_name, summary_text[:280]


async def bridge_browser_to_pico(
    browser_ws: WebSocket,
    pico_ws: aiohttp.ClientWebSocketResponse,
) -> None:
    while True:
        raw = await browser_ws.receive_text()
        data = json.loads(raw)
        if data.get("type") != "message.send":
            continue
        content = str(data.get("content", "")).strip()
        if not content:
            continue
        await pico_ws.send_json(
            {
                "type": "message.send",
                "id": secrets.token_hex(8),
                "payload": {"content": content},
            }
        )


async def bridge_pico_to_browser(
    browser_ws: WebSocket,
    pico_ws: aiohttp.ClientWebSocketResponse,
) -> None:
    async for msg in pico_ws:
        if msg.type != aiohttp.WSMsgType.TEXT:
            continue
        data = json.loads(msg.data)
        payload = data.get("payload") or {}
        event_type = data.get("type", "")
        if event_type in {"message.create", "message.update"}:
            await browser_ws.send_json(
                {
                    "type": event_type,
                    "message_id": payload.get("message_id") or data.get("id"),
                    "content": payload.get("content", ""),
                    "thought": bool(payload.get("thought")),
                    "session_id": data.get("session_id"),
                }
            )
        elif event_type in {"typing.start", "typing.stop"}:
            await browser_ws.send_json({"type": event_type, "session_id": data.get("session_id")})
        elif event_type == "error":
            await browser_ws.send_json(
                {
                    "type": "error",
                    "code": payload.get("code"),
                    "message": payload.get("message", "erro"),
                    "session_id": data.get("session_id"),
                }
            )
        else:
            tool_name, summary = summarize_event(event_type, payload)
            if tool_name or event_type.startswith("tool") or "tool" in event_type or "hook" in event_type:
                await browser_ws.send_json(
                    {
                        "type": "tool.event",
                        "event_type": event_type,
                        "tool_name": tool_name,
                        "summary": summary,
                        "session_id": data.get("session_id"),
                    }
                )
            else:
                await browser_ws.send_json(
                    {
                        "type": event_type or "event",
                        "summary": summary,
                        "session_id": data.get("session_id"),
                    }
                )


async def open_pico_ws(tenant: str, session_id: str):
    if not PICO_TOKEN:
        raise RuntimeError("TENANT_CHAT_PICO_TOKEN ausente")
    container_name = f"{CONTAINER_PREFIX}{tenant}"
    pico_url = f"ws://{container_name}:{PICO_PORT}/pico/ws?session_id={session_id}"
    client_session = aiohttp.ClientSession()
    try:
        pico_ws = await client_session.ws_connect(
            pico_url,
            headers={
                "Authorization": f"Bearer {PICO_TOKEN}",
                "Origin": SCAN_HOST,
            },
            heartbeat=25,
        )
        return client_session, pico_ws
    except Exception:
        await client_session.close()
        raise


@app.get("/auth/login", response_class=HTMLResponse)
async def auth_login(request: Request, next: str = "/chat"):
    if is_authenticated(request):
        return RedirectResponse(next, status_code=303)
    return HTMLResponse(login_html(next))


@app.post("/auth/login")
async def auth_login_submit(request: Request):
    form = await request.form()
    password = str(form.get("password", ""))
    next_path = str(form.get("next", "/chat")) or "/chat"
    if OPS_PASSWORD and not secrets.compare_digest(password, OPS_PASSWORD):
        return HTMLResponse(login_html(next_path, "Senha invalida."), status_code=401)
    response = RedirectResponse(next_path, status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        build_session_cookie(),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


@app.post("/auth/logout")
async def auth_logout():
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "tenants": len(list_tenants())}


@app.get("/chat", response_class=HTMLResponse)
async def chat_index(request: Request):
    if not is_authenticated(request):
        return HTMLResponse(login_html(str(request.url.path)), status_code=401)
    tenant = tenant_from_host(request.headers.get("host", ""))
    if tenant:
        return tenant_html_response(tenant)
    return HTMLResponse(build_index_html(list_tenants()))


@app.get("/chat/{tenant}", response_class=HTMLResponse)
async def chat_tenant(tenant: str, request: Request):
    if not is_authenticated(request):
        return HTMLResponse(login_html(f"/chat/{tenant}"), status_code=401)
    slug = normalize_slug(tenant)
    if not tenant_exists(slug):
        raise HTTPException(status_code=404, detail="tenant nao encontrado")
    return tenant_html_response(slug)


@app.get("/api/chat/tenants")
async def api_chat_tenants(request: Request):
    require_auth(request)
    return {"tenants": list_tenants()}


@app.get("/api/chat/{tenant}/status")
async def api_chat_tenant_status(tenant: str, request: Request):
    require_auth(request)
    slug = normalize_slug(tenant)
    return {
        "tenant": slug,
        "exists": tenant_exists(slug),
        "qr_url": f"{SCAN_HOST}/tenant/{slug}",
        "health_url": f"https://{slug}{TENANT_SUFFIX}/health",
    }


@app.get("/chat/public/{tenant}/pdf/{filename}")
async def public_tenant_pdf(tenant: str, filename: str):
    file_path = resolve_public_pdf_path(tenant, filename)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(file_path, media_type="application/pdf", filename=file_path.name)


@app.websocket("/chat/ws")
async def tenant_host_ws(websocket: WebSocket):
    if not is_websocket_authenticated(websocket):
        await websocket.close(code=1008, reason="unauthorized")
        return
    tenant = tenant_from_host(websocket.headers.get("host", ""))
    if not tenant:
        await websocket.close(code=1008, reason="tenant nao resolvido")
        return
    await websocket_bridge(websocket, tenant)


@app.websocket("/chat/{tenant}/ws")
async def tenant_slug_ws(websocket: WebSocket, tenant: str):
    if not is_websocket_authenticated(websocket):
        await websocket.close(code=1008, reason="unauthorized")
        return
    await websocket_bridge(websocket, tenant)


async def websocket_bridge(websocket: WebSocket, tenant: str):
    slug = normalize_slug(tenant)
    if not tenant_exists(slug):
        await websocket.close(code=1008, reason="tenant nao encontrado")
        return
    session_id = websocket.query_params.get("session_id") or secrets.token_hex(16)
    await websocket.accept()
    client_session = None
    pico_ws = None
    try:
        client_session, pico_ws = await open_pico_ws(slug, session_id)
        await websocket.send_json({"type": "session.ready", "tenant": slug, "session_id": session_id})

        browser_task = asyncio.create_task(bridge_browser_to_pico(websocket, pico_ws))
        pico_task = asyncio.create_task(bridge_pico_to_browser(websocket, pico_ws))

        done, pending = await asyncio.wait(
            {browser_task, pico_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        for task in done:
            task.result()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        with suppress(Exception):
            await websocket.send_json({"type": "error", "message": f"Falha ao conectar ao tenant {slug}: {exc}"})
    finally:
        if pico_ws is not None:
            with suppress(Exception):
                await pico_ws.close()
        if client_session is not None:
            with suppress(Exception):
                await client_session.close()
        with suppress(Exception):
            await websocket.close()


@app.get("/")
async def root():
    return RedirectResponse("/chat", status_code=302)
