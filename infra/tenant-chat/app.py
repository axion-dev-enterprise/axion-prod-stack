import asyncio
import html
import json
import os
import re
import secrets
from contextlib import suppress
from typing import Optional

import aiohttp
import docker
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

SITE_TITLE = os.getenv("TENANT_CHAT_SITE_TITLE", "AXION Tenant Chat")
PICO_TOKEN = os.getenv("TENANT_CHAT_PICO_TOKEN", "")
PICO_PORT = int(os.getenv("TENANT_CHAT_PICO_PORT", "18790"))
TENANT_SUFFIX = os.getenv("TENANT_CHAT_TENANT_SUFFIX", ".flow.axionenterprise.cloud")
CONTAINER_PREFIX = os.getenv("TENANT_CHAT_CONTAINER_PREFIX", "picoclaw-")
SCAN_HOST = os.getenv("TENANT_CHAT_SCAN_HOST", "https://scan.axionenterprise.cloud")
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


def list_tenants() -> list[str]:
    tenants = []
    for container in docker_client.containers.list():
        if not container.name.startswith(CONTAINER_PREFIX):
            continue
        slug = container.name.replace(CONTAINER_PREFIX, "", 1)
        if SLUG_RE.match(slug):
            tenants.append(slug)
    return sorted(set(tenants))


def build_index_html(tenants: list[str]) -> str:
    cards = []
    for slug in tenants:
        cards.append(
            f"""
            <a href="/chat/{html.escape(slug)}" class="card">
              <div class="tenant-name">{html.escape(slug)}</div>
              <div class="tenant-actions">
                <span>Abrir chat</span>
                <span class="muted">WebSocket</span>
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
        .wrap {{ max-width: 1040px; margin: 0 auto; padding: 48px 24px; }}
        h1 {{ margin: 0 0 12px; font-size: 44px; }}
        p {{ margin: 0 0 28px; color: var(--muted); max-width: 720px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
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
        .tenant-name {{ font-size: 22px; font-weight: 700; margin-bottom: 10px; }}
        .tenant-actions {{ display: flex; justify-content: space-between; color: var(--muted); font-size: 14px; }}
        .empty {{
          border: 1px dashed var(--border);
          border-radius: 24px;
          padding: 32px;
          color: var(--muted);
          text-align: center;
          background: rgba(255,255,255,0.02);
        }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <h1>{html.escape(SITE_TITLE)}</h1>
        <p>Chat custom por tenant, usando o canal Pico nativo do PicoClaw por WebSocket sem expor token no navegador.</p>
        <div class="grid">{''.join(cards)}</div>
      </div>
    </body>
    </html>
    """


def build_chat_html(slug: str) -> str:
    escaped_slug = html.escape(slug)
    ws_path = f"/chat/{escaped_slug}/ws"
    qr_url = f"{SCAN_HOST}/tenant/{escaped_slug}"
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
          --panel: rgba(14, 23, 34, 0.78);
          --border: rgba(255,255,255,0.08);
          --text: #ecf3ff;
          --muted: #8ea3b8;
          --assistant: #101c2b;
          --user: #1282d8;
          --shadow: rgba(0,0,0,.26);
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: "Segoe UI", system-ui, sans-serif;
          background: radial-gradient(circle at top, #153353 0%, #06111a 48%, #04070d 100%);
          color: var(--text);
        }}
        .layout {{ max-width: 1220px; margin: 0 auto; padding: 28px 20px 32px; }}
        .header {{
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 20px;
        }}
        .title-block h1 {{ margin: 0 0 6px; font-size: 38px; }}
        .title-block p {{ margin: 0; color: var(--muted); }}
        .header a {{
          color: var(--text);
          text-decoration: none;
          border: 1px solid var(--border);
          border-radius: 999px;
          padding: 10px 14px;
          background: rgba(255,255,255,0.04);
        }}
        .stack {{
          display: grid;
          grid-template-columns: 1.6fr .8fr;
          gap: 18px;
        }}
        .panel {{
          border: 1px solid var(--border);
          border-radius: 28px;
          background: var(--panel);
          backdrop-filter: blur(16px);
          box-shadow: 0 12px 40px var(--shadow);
        }}
        .chat-panel {{ padding: 18px; min-height: 72vh; display: flex; flex-direction: column; }}
        .meta {{
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 6px 6px 18px;
        }}
        .status {{ color: var(--muted); font-size: 14px; }}
        .messages {{
          flex: 1;
          overflow: auto;
          padding: 8px 4px 12px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }}
        .bubble {{
          max-width: min(82%, 760px);
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
          min-height: 62px;
          max-height: 220px;
          resize: vertical;
          border-radius: 18px;
          border: 1px solid var(--border);
          background: rgba(255,255,255,0.04);
          color: var(--text);
          padding: 14px 16px;
          font: inherit;
        }}
        button {{
          border: none;
          border-radius: 18px;
          padding: 0 18px;
          min-width: 132px;
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
        .muted {{ color: var(--muted); }}
        .mono {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
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
            <h1>Chat {escaped_slug}</h1>
            <p>Canal WebSocket custom do tenant <span class="mono">{escaped_slug}</span>.</p>
          </div>
          <a href="/chat">Todos os tenants</a>
        </div>
        <div class="stack">
          <section class="panel chat-panel">
            <div class="meta">
              <div class="status" id="status">Conectando...</div>
              <div class="muted mono" id="session-label">session: preparando</div>
            </div>
            <div class="messages" id="messages"></div>
            <div class="typing" id="typing">PicoClaw está digitando...</div>
            <form class="composer" id="composer">
              <textarea id="input" placeholder="Digite sua mensagem para o tenant {escaped_slug}..."></textarea>
              <button type="submit">Enviar</button>
            </form>
          </section>
          <aside class="panel side-panel">
            <div class="side-card">
              <strong>Tenant</strong>
              <div class="muted mono" style="margin-top:8px">{escaped_slug}</div>
            </div>
            <div class="side-card">
              <strong>Onboarding</strong>
              <div class="muted" style="margin-top:8px">Se o WhatsApp ainda não estiver pareado, abra o QR isolado deste tenant.</div>
              <div style="margin-top:12px"><a href="{html.escape(qr_url)}" target="_blank" rel="noreferrer" style="color:#7ed9ff">Abrir QR deste tenant</a></div>
            </div>
            <div class="side-card">
              <strong>Sessão</strong>
              <div class="muted" style="margin-top:8px">A conversa fica isolada por aba e navegador via session id único.</div>
            </div>
          </aside>
        </div>
      </div>
      <script>
        const tenant = {json.dumps(slug)};
        const sessionKey = `axion-chat:${{tenant}}`;
        const storedSession = localStorage.getItem(sessionKey);
        const sessionId = storedSession || (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2));
        localStorage.setItem(sessionKey, sessionId);

        const messagesEl = document.getElementById("messages");
        const typingEl = document.getElementById("typing");
        const inputEl = document.getElementById("input");
        const statusEl = document.getElementById("status");
        const sessionLabelEl = document.getElementById("session-label");
        const composerEl = document.getElementById("composer");
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

        function upsertAssistantMessage(id, text) {{
          if (id && messageMap.has(id)) {{
            messageMap.get(id).textContent = text;
            return;
          }}
          appendBubble("assistant", text, id);
        }}

        function setStatus(text) {{
          statusEl.textContent = text;
        }}

        const scheme = location.protocol === "https:" ? "wss" : "ws";
        const socket = new WebSocket(`${{scheme}}://${{location.host}}{ws_path}?session_id=${{encodeURIComponent(sessionId)}}`);

        socket.addEventListener("open", () => {{
          setStatus("Conectado");
          appendBubble("system", "Conexão WebSocket ativa com o tenant.", null);
        }});

        socket.addEventListener("message", (event) => {{
          try {{
            const data = JSON.parse(event.data);
            if (data.type === "session.ready") {{
              setStatus("Sessão pronta");
              return;
            }}
            if (data.type === "typing.start") {{
              typingEl.style.display = "block";
              return;
            }}
            if (data.type === "typing.stop") {{
              typingEl.style.display = "none";
              return;
            }}
            if (data.type === "message.create" || data.type === "message.update") {{
              typingEl.style.display = "none";
              if (data.thought) return;
              upsertAssistantMessage(data.message_id || null, data.content || "");
              return;
            }}
            if (data.type === "error") {{
              appendBubble("system", `Erro: ${{data.message || "falha desconhecida"}}`, null);
            }}
          }} catch {{
            appendBubble("system", "Falha ao interpretar uma mensagem do socket.", null);
          }}
        }});

        socket.addEventListener("close", () => {{
          setStatus("Desconectado");
          typingEl.style.display = "none";
          appendBubble("system", "A conexão foi encerrada. Recarregue a página para reconectar.", null);
        }});

        socket.addEventListener("error", () => {{
          setStatus("Erro de conexão");
        }});

        composerEl.addEventListener("submit", (event) => {{
          event.preventDefault();
          const content = inputEl.value.trim();
          if (!content || socket.readyState !== WebSocket.OPEN) return;
          appendBubble("user", content, null);
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


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "tenants": len(list_tenants())}


@app.get("/chat", response_class=HTMLResponse)
async def chat_index(request: Request):
    tenant = tenant_from_host(request.headers.get("host", ""))
    if tenant:
        return tenant_html_response(tenant)
    return HTMLResponse(build_index_html(list_tenants()))


@app.get("/chat/{tenant}", response_class=HTMLResponse)
async def chat_tenant(tenant: str):
    return tenant_html_response(tenant)


@app.get("/api/chat/tenants")
async def api_chat_tenants():
    return {"tenants": list_tenants()}


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


@app.websocket("/chat/ws")
async def tenant_host_ws(websocket: WebSocket):
    tenant = tenant_from_host(websocket.headers.get("host", ""))
    if not tenant:
        await websocket.close(code=1008, reason="tenant nao resolvido")
        return
    await websocket_bridge(websocket, tenant)


@app.websocket("/chat/{tenant}/ws")
async def tenant_slug_ws(websocket: WebSocket, tenant: str):
    await websocket_bridge(websocket, tenant)


async def websocket_bridge(websocket: WebSocket, tenant: str):
    slug = normalize_slug(tenant)
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
    return JSONResponse({"status": "ok", "service": "tenant-chat"})
