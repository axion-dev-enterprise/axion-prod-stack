import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI()

CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", "").strip()
CF_API_TOKEN = os.getenv("CF_API_TOKEN", "").strip()
DEFAULT_MODEL = os.getenv("CF_WORKERS_MODEL", "@cf/meta/llama-3.1-8b-instruct").strip()
UPSTREAM_BASE = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/v1"


def normalize_model(model: str | None) -> str:
    raw = (model or "").strip()
    if not raw:
        return DEFAULT_MODEL
    if raw.startswith("openai/@cf/"):
        return raw[len("openai/") :]
    if raw.startswith("@cf/"):
        return raw
    return DEFAULT_MODEL


async def forward_chat(payload: dict[str, Any]) -> JSONResponse:
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        raise HTTPException(status_code=500, detail="Cloudflare credentials missing")

    upstream_payload = dict(payload)
    upstream_payload["model"] = normalize_model(payload.get("model"))

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{UPSTREAM_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {CF_API_TOKEN}",
                "Content-Type": "application/json",
            },
            json=upstream_payload,
        )

    return JSONResponse(status_code=response.status_code, content=response.json())


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat/completions")
async def chat_completions(request: Request) -> JSONResponse:
    return await forward_chat(await request.json())


@app.post("/v1/chat/completions")
async def chat_completions_v1(request: Request) -> JSONResponse:
    return await forward_chat(await request.json())
