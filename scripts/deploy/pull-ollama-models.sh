#!/usr/bin/env bash
set -euo pipefail
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
FAST_MODEL="${OLLAMA_MODEL_FAST:-qwen2.5:3b-instruct-q4_K_M}"
EMBED_MODEL="${OLLAMA_MODEL_EMBED:-nomic-embed-text}"
curl -fsS "$OLLAMA_URL/api/pull" -d "{"name":"$FAST_MODEL"}"
curl -fsS "$OLLAMA_URL/api/pull" -d "{"name":"$EMBED_MODEL"}"
echo "Modelos Ollama solicitados."
