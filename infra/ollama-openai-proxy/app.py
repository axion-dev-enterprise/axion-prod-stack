import json
import os
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://172.20.0.1:11434").rstrip("/").removesuffix("/v1")
DEFAULT_MODEL = os.getenv("OLLAMA_PROXY_DEFAULT_MODEL", "qwen2.5:1.5b").strip()
REQUEST_TIMEOUT = float(os.getenv("OLLAMA_PROXY_TIMEOUT_SECONDS", "300"))


def normalize_model(model: str | None) -> str:
    raw = (model or "").strip()
    if raw.startswith("local/"):
        return raw.split("/", 1)[1]
    if raw:
        return raw
    return DEFAULT_MODEL


def flatten_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized = []
    for message in messages:
        normalized.append(
            {
                "role": str(message.get("role", "user")),
                "content": flatten_content(message.get("content", "")),
            }
        )
    return normalized


async def call_ollama(payload: dict[str, Any]) -> dict[str, Any]:
    model = normalize_model(payload.get("model"))
    options: dict[str, Any] = {}
    if payload.get("temperature") is not None:
        options["temperature"] = payload.get("temperature")
    if payload.get("max_tokens") is not None:
        options["num_predict"] = payload.get("max_tokens")

    upstream_payload = {
        "model": model,
        "messages": normalize_messages(payload.get("messages", [])),
        "stream": False,
    }
    if options:
        upstream_payload["options"] = options

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=upstream_payload)
        response.raise_for_status()
        data = response.json()

    content = data.get("message", {}).get("content", "")
    usage = {
        "prompt_tokens": data.get("prompt_eval_count", 0),
        "completion_tokens": data.get("eval_count", 0),
        "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
    }
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "system_fingerprint": "fp_ollama_proxy",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": usage,
    }


def sse_lines(response_json: dict[str, Any]):
    choice = response_json["choices"][0]
    content = choice["message"]["content"]
    chunk_id = response_json["id"]
    created = response_json["created"]
    model = response_json["model"]

    first = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "system_fingerprint": response_json["system_fingerprint"],
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}, "finish_reason": None}],
    }
    final = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "system_fingerprint": response_json["system_fingerprint"],
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(first, ensure_ascii=False)}\n\n"
    yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = await request.json()
    response_json = await call_ollama(payload)
    if payload.get("stream"):
        return StreamingResponse(sse_lines(response_json), media_type="text/event-stream")
    return JSONResponse(response_json)


@app.post("/chat/completions")
async def chat_completions_short(request: Request):
    return await chat_completions(request)
