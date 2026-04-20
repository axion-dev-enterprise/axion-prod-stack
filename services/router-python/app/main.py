import os
from typing import Literal, Optional
import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY_FREE = os.getenv("OPENROUTER_API_KEY_FREE", "")
OPENROUTER_API_KEY_PAID = os.getenv("OPENROUTER_API_KEY_PAID", "")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "https://example.com")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "AXION Router")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
INTERNAL_SHARED_TOKEN = os.getenv("INTERNAL_SHARED_TOKEN", "")

MODEL_MAP = {
    "free_router": os.getenv("OPENROUTER_MODEL_FREE_ROUTER", "openrouter/free"),
    "free_fixed": os.getenv("OPENROUTER_MODEL_FREE_FIXED", "google/gemma-3-4b-it:free"),
    "cheap_fast": os.getenv("OPENROUTER_MODEL_CHEAP_FAST", "openai/gpt-4.1-nano"),
    "cheap_main": os.getenv("OPENROUTER_MODEL_CHEAP_MAIN", "openai/gpt-4.1-mini"),
    "balanced": os.getenv("OPENROUTER_MODEL_BALANCED", "qwen/qwen3-8b"),
    "premium": os.getenv("OPENROUTER_MODEL_PREMIUM", "google/gemma-4-26b-a4b-it"),
    "ollama_fast": os.getenv("OLLAMA_MODEL_FAST", "qwen2.5:3b-instruct-q4_K_M"),
}

TASK_POLICY = {
    "classify": {"target": "ollama_fast"},
    "rewrite": {"target": "free_fixed"},
    "summarize": {"target": "cheap_fast"},
    "qa": {"target": "cheap_main"},
    "agent": {"target": "balanced"},
    "premium": {"target": "premium"},
}

class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str

class ChatRequest(BaseModel):
    task_type: Literal["classify", "rewrite", "summarize", "qa", "agent", "premium"] = "qa"
    messages: list[Message]
    force_target: Optional[str] = None
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 800

app = FastAPI(title="AXION Router Python")

def require_auth(token: str | None):
    if INTERNAL_SHARED_TOKEN and token != INTERNAL_SHARED_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

@app.get("/health")
async def health():
    return {"ok": True, "service": "router-python"}

@app.get("/models")
async def models(x_internal_token: Optional[str] = Header(default=None)):
    require_auth(x_internal_token)
    return {"models": MODEL_MAP, "task_policy": TASK_POLICY}

@app.post("/route/chat")
async def route_chat(payload: ChatRequest, x_internal_token: Optional[str] = Header(default=None)):
    require_auth(x_internal_token)
    target = payload.force_target or TASK_POLICY[payload.task_type]["target"]
    model = MODEL_MAP[target]

    if target.startswith("ollama"):
        body = {
            "model": model,
            "messages": [m.model_dump() for m in payload.messages],
            "stream": False,
            "options": {"temperature": payload.temperature},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=body)
            resp.raise_for_status()
            data = resp.json()
        return {"provider": "ollama", "target": target, "model": model, "content": data.get("message", {}).get("content", ""), "raw": data}

    key = OPENROUTER_API_KEY_FREE if target in {"free_router", "free_fixed"} else OPENROUTER_API_KEY_PAID
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_SITE_URL,
        "X-Title": OPENROUTER_APP_NAME,
    }
    body = {
        "model": model,
        "messages": [m.model_dump() for m in payload.messages],
        "temperature": payload.temperature,
        "max_tokens": payload.max_tokens,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{OPENROUTER_BASE_URL}/chat/completions", headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
    return {"provider": "openrouter", "target": target, "model": model, "content": data["choices"][0]["message"]["content"], "raw": data}
