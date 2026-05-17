import hmac
import html
import os
import re
import secrets
import time
from datetime import datetime
from hashlib import sha256
from typing import List, Optional, Tuple

import docker
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

app = FastAPI()

CONTAINER_PREFIX = os.getenv("QR_SCANNER_CONTAINER_PREFIX", "picoclaw-")
SITE_TITLE = os.getenv("QR_SCANNER_SITE_TITLE", "AXION QR Dashboard")
OPS_PASSWORD = os.getenv("AXION_OPS_PASSWORD", os.getenv("TENANT_ADMIN_TOKEN", ""))
SESSION_SECRET = os.getenv("AXION_OPS_SESSION_SECRET", OPS_PASSWORD or "axion-ops")
COOKIE_NAME = os.getenv("AXION_OPS_COOKIE_NAME", "axion_ops")
SESSION_TTL_SECONDS = int(os.getenv("AXION_OPS_SESSION_TTL_SECONDS", "43200"))
ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
QR_CHARS = {"\u2588", "\u2580", "\u2584", " "}
MOJIBAKE_REPLACEMENTS = {
    "â–ˆ": "\u2588",
    "â–€": "\u2580",
    "â–„": "\u2584",
}

try:
    client = docker.from_env()
except Exception:
    client = docker.DockerClient(base_url="unix://var/run/docker.sock")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def normalize_qr_chars(text: str) -> str:
    clean = strip_ansi(text)
    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        clean = clean.replace(bad, good)
    return clean


def sign_value(value: str) -> str:
    return hmac.new(SESSION_SECRET.encode("utf-8"), value.encode("utf-8"), sha256).hexdigest()


def build_session_cookie() -> str:
    issued = str(int(time.time()))
    nonce = secrets.token_hex(8)
    payload = f"{issued}:{nonce}"
    return f"{payload}:{sign_value(payload)}"


def is_authenticated(request: Request) -> bool:
    if not OPS_PASSWORD:
        return True
    token = request.cookies.get(COOKIE_NAME, "")
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
          --bg: #03060a;
          --panel: rgba(10, 18, 29, 0.88);
          --border: rgba(255,255,255,0.08);
          --text: #ecf4ff;
          --muted: #91a5bb;
          --danger: #ff8b8b;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          min-height: 100vh;
          display: grid;
          place-items: center;
          background: radial-gradient(circle at top, #11233d 0%, #050810 58%, #020407 100%);
          color: var(--text);
          font-family: "Segoe UI", system-ui, sans-serif;
          padding: 24px;
        }}
        .card {{
          width: min(100%, 420px);
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
        <h1>Acesso operacional</h1>
        <p>Entre para visualizar QR codes, eventos recentes e controlar os tenants sem expor o console publicamente.</p>
        {error_block}
        <input type="hidden" name="next" value="{html.escape(next_path)}" />
        <label for="password">Senha de acesso</label>
        <input id="password" name="password" type="password" autocomplete="current-password" required />
        <button type="submit">Entrar</button>
      </form>
    </body>
    </html>
    """


def list_picoclaw_containers():
    containers = client.containers.list()
    return sorted(
        [c for c in containers if c.name.startswith(CONTAINER_PREFIX)],
        key=lambda c: c.name,
    )


def is_qr_line(line: str) -> bool:
    normalized = normalize_qr_chars(line).strip()
    return bool(normalized) and set(normalized) <= QR_CHARS and "\u2588" in normalized


def extract_qr(logs: str) -> str:
    lines = [normalize_qr_chars(line) for line in logs.splitlines()]
    markers = [i for i, line in enumerate(lines) if "Scan this QR code" in line]
    if not markers:
        return ""

    last_marker = markers[-1]
    trailing_lines = lines[last_marker + 1 :]
    if any("event=timeout" in line.lower() for line in trailing_lines):
        return ""

    blocks: List[List[str]] = []
    current: List[str] = []
    for line in trailing_lines:
        candidate = line.rstrip()
        if is_qr_line(candidate):
            current.append(candidate)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    if not blocks:
        return ""
    return "\n".join(blocks[-1])


def extract_last_qr_timestamp(logs: str) -> Optional[str]:
    lines = [normalize_qr_chars(line) for line in logs.splitlines()]
    markers = [line for line in lines if "Scan this QR code" in line]
    if not markers:
        return None
    line = markers[-1]
    match = re.match(r"^(\d{2}:\d{2}:\d{2})", line)
    return match.group(1) if match else None


def derive_status(logs: str, qr: str) -> Tuple[str, str]:
    lowered = logs.lower()
    if "event=timeout" in lowered:
        timeout_pos = lowered.rfind("event=timeout")
        qr_pos = lowered.rfind("scan this qr code")
        if timeout_pos > qr_pos:
            return "QR expirado", "amber"
    if qr:
        return "QR pronto", "sky"
    if "scan this qr code" in lowered:
        return "Gerando QR", "sky"
    if "login success" in lowered or "connected" in lowered:
        return "Connected", "emerald"
    if "error" in lowered or "failed" in lowered:
        return "Erro", "rose"
    if "ready" in lowered:
        return "Pronto", "lime"
    return "Inicializando", "slate"


def clean_recent_logs(logs: str) -> List[str]:
    recent: List[str] = []
    for raw in logs.splitlines():
        clean = normalize_qr_chars(raw).strip()
        if not clean:
            continue
        if is_qr_line(clean):
            continue
        if clean.startswith("\u2588\u2588\u2588\u2588\u2588\u2588") or "PicoClaw is a lightweight personal AI assistant" in clean:
            continue
        recent.append(clean)
    return recent[-8:]


def qr_to_matrix(qr: str) -> List[List[int]]:
    if not qr:
        return []
    rows: List[List[int]] = []
    for line in qr.splitlines():
        upper: List[int] = []
        lower: List[int] = []
        for char in line:
            if char == "\u2588":
                upper.append(1)
                lower.append(1)
            elif char == "\u2580":
                upper.append(1)
                lower.append(0)
            elif char == "\u2584":
                upper.append(0)
                lower.append(1)
            else:
                upper.append(0)
                lower.append(0)
        rows.append(upper)
        rows.append(lower)
    return rows


def qr_matrix_to_html(qr: str) -> str:
    matrix = qr_to_matrix(qr)
    if not matrix:
        return '<div class="qr-empty">Aguardando um QR limpo do WhatsApp...</div>'

    size = len(matrix[0])
    quiet_zone = 4
    total = size + quiet_zone * 2
    rects: List[str] = []
    for row_index, row in enumerate(matrix):
        for col_index, value in enumerate(row):
            if value:
                rects.append(
                    f'<rect x="{col_index + quiet_zone}" y="{row_index + quiet_zone}" width="1" height="1" fill="#05070b" />'
                )
    return (
        f'<svg class="qr-svg" viewBox="0 0 {total} {total}" role="img" aria-label="QR code do WhatsApp" '
        'xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">'
        f'<rect width="{total}" height="{total}" fill="#ffffff" />'
        + "".join(rects)
        + "</svg>"
    )


def get_tenant_details(container):
    logs = container.logs(tail=1200).decode("utf-8", errors="ignore")
    qr = extract_qr(logs)
    status_text, status_color = derive_status(logs, qr)
    qr_timestamp = extract_last_qr_timestamp(logs)
    return {
        "name": container.name.replace(CONTAINER_PREFIX, "", 1),
        "id": container.id[:12],
        "status": container.status,
        "status_text": status_text,
        "status_color": status_color,
        "qr": qr,
        "qr_timestamp": qr_timestamp,
        "recent_logs": clean_recent_logs(logs),
    }


def ensure_fresh_tenant_details(name: str):
    container = find_picoclaw_container(name)
    details = get_tenant_details(container)
    if details["status_text"] == "QR expirado" and not details["qr"]:
        container.restart(timeout=10)
        time.sleep(4)
        container.reload()
        details = get_tenant_details(container)
    return container, details


STATUS_COLORS = {
    "emerald": ("text-emerald-300", "bg-emerald-500"),
    "amber": ("text-amber-300", "bg-amber-500"),
    "sky": ("text-sky-300", "bg-sky-500"),
    "lime": ("text-lime-300", "bg-lime-500"),
    "rose": ("text-rose-300", "bg-rose-500"),
    "slate": ("text-slate-300", "bg-slate-500"),
}


def page_shell(title: str, body_html: str, subtitle: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>{html.escape(SITE_TITLE)}</title>
      <script src="https://cdn.tailwindcss.com"></script>
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
      <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: radial-gradient(circle at top, #13213b 0%, #06070b 52%, #030406 100%); color: #f8fafc; }}
        .glass {{ background: rgba(15, 23, 42, 0.68); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.08); }}
        .qr-shell {{ background: linear-gradient(180deg, #f8fbff 0%, #dde7f1 100%); box-shadow: inset 0 0 0 1px rgba(15,23,42,0.06); display: flex; justify-content: center; }}
        .qr-svg {{ display: block; width: min(100%, 520px); aspect-ratio: 1 / 1; background: #ffffff; border-radius: 18px; padding: 16px; }}
        .qr-empty {{ min-height: 320px; display: grid; place-items: center; color: #334155; font-weight: 600; text-align: center; }}
        .status-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 999px; box-shadow: 0 0 20px currentColor; }}
        .countdown-pulse {{ animation: pulse 1.4s ease-in-out infinite; }}
        @keyframes pulse {{
          0% {{ opacity: 0.65; }}
          50% {{ opacity: 1; }}
          100% {{ opacity: 0.65; }}
        }}
      </style>
    </head>
    <body class="min-h-screen">
      <div class="mx-auto max-w-7xl px-6 py-10">
        <header class="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div class="mb-3 inline-flex items-center gap-3 rounded-full border border-sky-400/20 bg-sky-400/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-sky-200">
              QR facil e monitoramento nativo
            </div>
            <h1 class="text-4xl font-extrabold tracking-tight md:text-5xl">{html.escape(title)}</h1>
            <p class="mt-3 max-w-3xl text-slate-300">{html.escape(subtitle)}</p>
          </div>
          <div class="flex items-center gap-3">
            <div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
              Atualizacao automatica a cada 5 segundos
            </div>
            <form method="post" action="/auth/logout">
              <button class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300 transition hover:bg-white/10">Sair</button>
            </form>
          </div>
        </header>
        <main>{body_html}</main>
      </div>
      <script>
        async function actionTenant(name, action, btn) {{
          const original = btn.innerText;
          btn.disabled = true;
          btn.innerText = "Processando...";
          try {{
            const resp = await fetch(`/api/tenant/${{name}}/${{action}}`, {{ method: "POST" }});
            const data = await resp.json();
            if (!resp.ok) {{
              throw new Error(data.error || data.detail || "Falha inesperada");
            }}
            window.location.reload();
          }} catch (err) {{
            alert(err.message);
            btn.disabled = false;
            btn.innerText = original;
          }}
        }}
        setTimeout(() => window.location.reload(), 5000);
      </script>
    </body>
    </html>
    """


def build_tenant_index(tenants):
    cards = []
    for tenant in tenants:
        text_class, dot_class = STATUS_COLORS[tenant["status_color"]]
        cards.append(
            f"""
            <a href="/tenant/{html.escape(tenant["name"])}" class="glass block rounded-3xl p-7 shadow-2xl shadow-black/20 transition hover:-translate-y-1 hover:border-sky-300/30">
              <div class="mb-5 flex items-start justify-between gap-4">
                <div>
                  <h3 class="text-2xl font-bold tracking-tight">{html.escape(tenant["name"])}</h3>
                  <div class="mt-2 flex items-center gap-2">
                    <span class="status-dot {dot_class}"></span>
                    <span class="text-xs font-semibold uppercase tracking-[0.24em] {text_class}">{html.escape(tenant["status_text"])}</span>
                  </div>
                </div>
                <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-[11px] text-slate-400">{tenant["id"]}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <div class="text-sm text-slate-300">Abrir QR isolado e eventos deste tenant</div>
                <div class="rounded-full border border-sky-300/20 bg-sky-300/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-sky-200">Entrar</div>
              </div>
            </a>
            """
        )

    if not cards:
        cards.append(
            """
            <section class="glass rounded-3xl p-10 text-center">
              <h3 class="text-2xl font-bold mb-3">Nenhuma instancia ativa</h3>
              <p class="text-slate-400">Suba um container `picoclaw-*` para ele aparecer automaticamente aqui.</p>
            </section>
            """
        )

    body = f'<div class="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3">{"".join(cards)}</div>'
    return page_shell(
        SITE_TITLE,
        body,
        "Indice isolado por tenant para abrir cada QR em uma pagina separada, sem misturar pareamentos de clientes diferentes.",
    )


def build_tenant_page(tenant):
    text_class, dot_class = STATUS_COLORS[tenant["status_color"]]
    qr_block = qr_matrix_to_html(tenant["qr"])
    recent_html = "<br>".join(html.escape(line) for line in tenant["recent_logs"])
    auto_recover_script = ""
    qr_info = ""
    if tenant.get("qr_timestamp"):
        qr_info = (
            f'<div class="mb-4 flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">'
            f'<span>Ultimo QR detectado as <strong class="text-white">{html.escape(tenant["qr_timestamp"])}</strong></span>'
            f'<span class="countdown-pulse rounded-full bg-amber-400/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-amber-200">Escaneie imediatamente</span>'
            f"</div>"
        )
    if tenant["status_text"] == "QR expirado":
        auto_recover_script = f"""
        <script>
          setTimeout(async () => {{
            const notice = document.getElementById("auto-recover-status");
            if (notice) {{
              notice.textContent = "QR expirado. Reiniciando a instancia para gerar um novo codigo...";
            }}
            try {{
              await fetch('/api/tenant/{html.escape(tenant["name"])}/restart', {{ method: 'POST' }});
            }} catch (err) {{
              console.error(err);
            }}
            setTimeout(() => window.location.reload(), 3500);
          }}, 900);
        </script>
        """
    body = f"""
    <div class="mb-6">
      <a href="/" class="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300 transition hover:bg-white/10">Voltar para tenants</a>
    </div>
    <section class="glass mx-auto max-w-4xl rounded-3xl p-8 shadow-2xl shadow-black/20">
      <div class="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 class="text-3xl font-bold tracking-tight">{html.escape(tenant["name"])}</h2>
          <div class="mt-2 flex items-center gap-2">
            <span class="status-dot {dot_class}"></span>
            <span class="text-xs font-semibold uppercase tracking-[0.24em] {text_class}">{html.escape(tenant["status_text"])}</span>
          </div>
        </div>
        <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-[11px] text-slate-400">{tenant["id"]}</span>
      </div>
      <div class="qr-shell rounded-2xl p-6 mb-4 overflow-auto">
        {qr_block}
      </div>
      {qr_info}
      <div class="mb-4 rounded-2xl border border-white/5 bg-white/5 p-4 text-sm text-slate-300">
        Renderizacao em SVG, com modulo fixo e contraste estavel para leitura no celular.
      </div>
      <div id="auto-recover-status" class="mb-4 text-sm text-slate-300"></div>
      <div class="grid grid-cols-2 gap-3 mb-4">
        <button type="button" onclick="actionTenant('{html.escape(tenant['name'])}', 'restart', this)" class="rounded-xl bg-sky-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-400">Gerar novo QR</button>
        <button type="button" onclick="window.location.reload()" class="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/10">Atualizar</button>
      </div>
      <div class="rounded-2xl border border-white/5 bg-white/5 p-4">
        <div class="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Ultimos eventos</div>
        <div class="font-mono text-xs leading-6 text-slate-300">{recent_html}</div>
      </div>
    </section>
    {auto_recover_script}
    """
    return page_shell(
        f"{SITE_TITLE} · {tenant['name']}",
        body,
        "Pagina isolada para pareamento rapido deste tenant, com QR limpo, reinicio rapido e eventos recentes do proprio container.",
    )


def find_picoclaw_container(name: str):
    try:
        return client.containers.get(f"{CONTAINER_PREFIX}{name}")
    except docker.errors.NotFound as exc:
        raise HTTPException(status_code=404, detail="Container nao encontrado.") from exc


@app.get("/auth/login", response_class=HTMLResponse)
async def auth_login(request: Request, next: str = "/"):
    if is_authenticated(request):
        return RedirectResponse(next, status_code=303)
    return HTMLResponse(login_html(next))


@app.post("/auth/login")
async def auth_login_submit(request: Request):
    form = await request.form()
    password = str(form.get("password", ""))
    next_path = str(form.get("next", "/")) or "/"
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


@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def index(request: Request):
    if not is_authenticated(request):
        return HTMLResponse(content=login_html("/"), status_code=401)
    tenants = [get_tenant_details(container) for container in list_picoclaw_containers()]
    return HTMLResponse(content=build_tenant_index(tenants))


@app.get("/tenant/{name}", response_class=HTMLResponse)
@app.head("/tenant/{name}", response_class=HTMLResponse)
async def tenant_page(name: str, request: Request):
    if not is_authenticated(request):
        return HTMLResponse(content=login_html(f"/tenant/{name}"), status_code=401)
    _, details = ensure_fresh_tenant_details(name)
    return HTMLResponse(content=build_tenant_page(details))


@app.get("/healthz")
@app.head("/healthz")
async def healthz():
    return {"status": "ok", "containers": len(list_picoclaw_containers())}


@app.get("/api/tenants")
async def api_tenants(request: Request):
    require_auth(request)
    return {"tenants": [get_tenant_details(container) for container in list_picoclaw_containers()]}


@app.get("/api/tenant/{name}")
async def api_tenant(name: str, request: Request):
    require_auth(request)
    _, details = ensure_fresh_tenant_details(name)
    return details


@app.post("/api/tenant/{name}/{action}")
async def tenant_action(name: str, action: str, request: Request):
    require_auth(request)
    container = find_picoclaw_container(name)

    if action != "restart":
        raise HTTPException(status_code=400, detail="Acao invalida.")

    container.restart(timeout=10)
    return JSONResponse({"message": f"Instancia {name} reiniciada com sucesso."})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
