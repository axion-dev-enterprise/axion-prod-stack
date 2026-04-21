import html
import os
import re
from datetime import datetime
import time
from typing import List, Optional, Tuple

import docker
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

CONTAINER_PREFIX = os.getenv("QR_SCANNER_CONTAINER_PREFIX", "picoclaw-")
SITE_TITLE = os.getenv("QR_SCANNER_SITE_TITLE", "AXION QR Dashboard")
ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
QR_CHARS = set("█▀▄ ")

try:
    client = docker.from_env()
except Exception:
    client = docker.DockerClient(base_url="unix://var/run/docker.sock")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def list_picoclaw_containers():
    containers = client.containers.list()
    return sorted(
        [c for c in containers if c.name.startswith(CONTAINER_PREFIX)],
        key=lambda c: c.name,
    )


def is_qr_line(line: str) -> bool:
    normalized = line.strip()
    return bool(normalized) and set(normalized) <= QR_CHARS and "█" in normalized


def extract_qr(logs: str) -> str:
    lines = [strip_ansi(line) for line in logs.splitlines()]
    markers = [i for i, line in enumerate(lines) if "Scan this QR code" in line]
    if not markers:
        return ""

    last_marker = markers[-1]
    trailing_lines = lines[last_marker + 1 :]
    if any("event=timeout" in line.lower() for line in trailing_lines):
        return ""

    lines = trailing_lines
    blocks: List[List[str]] = []
    current: List[str] = []

    for line in lines:
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
    lines = [strip_ansi(line) for line in logs.splitlines()]
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
        clean = strip_ansi(raw).strip()
        if not clean:
            continue
        if is_qr_line(clean):
            continue
        if clean.startswith("██████") or "PicoClaw is a lightweight personal AI assistant" in clean:
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
            if char == "█":
                upper.append(1)
                lower.append(1)
            elif char == "▀":
                upper.append(1)
                lower.append(0)
            elif char == "▄":
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

    modules: List[str] = []
    size = len(matrix[0])
    for row in matrix:
        for value in row:
            cls = "qr-on" if value else "qr-off"
            modules.append(f'<span class="qr-cell {cls}"></span>')

    return (
        f'<div class="qr-grid" style="grid-template-columns: repeat({size}, 1fr)">'
        + "".join(modules)
        + "</div>"
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
        .qr-grid {{ display: grid; width: min(100%, 520px); aspect-ratio: 1 / 1; background: #ffffff; padding: 16px; border-radius: 18px; }}
        .qr-cell {{ width: 100%; aspect-ratio: 1 / 1; }}
        .qr-on {{ background: #05070b; }}
        .qr-off {{ background: #ffffff; }}
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
          <div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
            Atualizacao automatica a cada 5 segundos
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
              notice.textContent = "QR expirado. Reiniciando a instância para gerar um novo código...";
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


@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def index(_: Request):
    tenants = [get_tenant_details(container) for container in list_picoclaw_containers()]
    return HTMLResponse(content=build_tenant_index(tenants))


@app.get("/tenant/{name}", response_class=HTMLResponse)
@app.head("/tenant/{name}", response_class=HTMLResponse)
async def tenant_page(name: str):
    _, details = ensure_fresh_tenant_details(name)
    return HTMLResponse(content=build_tenant_page(details))


@app.get("/healthz")
@app.head("/healthz")
async def healthz():
    return {"status": "ok", "containers": len(list_picoclaw_containers())}


@app.get("/api/tenants")
async def api_tenants():
    return {"tenants": [get_tenant_details(container) for container in list_picoclaw_containers()]}


@app.get("/api/tenant/{name}")
async def api_tenant(name: str):
    _, details = ensure_fresh_tenant_details(name)
    return details


@app.post("/api/tenant/{name}/{action}")
async def tenant_action(name: str, action: str):
    container = find_picoclaw_container(name)

    if action != "restart":
        raise HTTPException(status_code=400, detail="Acao invalida.")

    container.restart(timeout=10)
    return JSONResponse({"message": f"Instancia {name} reiniciada com sucesso."})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
