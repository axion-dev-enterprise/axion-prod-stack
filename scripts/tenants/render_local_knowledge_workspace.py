#!/usr/bin/env python3
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


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: render_local_knowledge_workspace.py <tenant-slug> <workspace-dir>", file=sys.stderr)
        return 1

    tenant_slug = sys.argv[1]
    workspace_dir = Path(sys.argv[2])
    tools_dir = workspace_dir / "tools"
    mempalace_dir = workspace_dir / "mempalace"
    wiki_dir = workspace_dir / "llm-wiki"

    chat_model = env("PICOCLAW_UPSTREAM_MODEL", env("PICOCLAW_DEFAULT_MODEL", "qwen2.5:1.5b"))
    embed_model = env("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    ollama_chat_host = env("OLLAMA_CHAT_BASE_URL", "http://ollama-openai-proxy:8021/v1")
    ollama_host = env("OLLAMA_BASE_URL", "http://172.20.0.1:11434/v1")
    ollama_embed_host = ollama_host.removesuffix("/v1")

    write_text(
        workspace_dir / "BOOTSTRAP.md",
        f"""
        # Workspace Bootstrap

        Tenant ativo: `{tenant_slug}`.

        Stack local:
        - chat e tools via proxy local do Ollama usando `{chat_model}`
        - embeddings via Ollama local usando `{embed_model}`
        - wiki local em `llm-wiki/`
        - memoria vetorial local em `mempalace/`

        Rotina recomendada:
        1. Ler `llm-wiki/README.md` e `llm-wiki/STACK.md`.
        2. Ler `SOUL.md` e `MEMORY.md` antes de interacoes longas.
        3. Atualizar os markdowns do `llm-wiki/` quando houver contexto novo.
        4. Executar `python3 /root/.picoclaw/workspace/tools/wiki_index.py` para reindexar.
        5. Consultar `python3 /root/.picoclaw/workspace/tools/wiki_search.py "consulta"` antes de responder temas internos.

        Regras:
        - use somente caminhos dentro do workspace
        - trate `llm-wiki/` como fonte canonica
        - trate `mempalace/` como cache semantico derivado, que pode ser regenerado
        - mantenha o tom natural, entusiasmado e proativo, sem soar robotico
        - use tools e skills quando elas reduzirem suposicoes, risco ou consumo de tokens
        - prefira perguntas curtas e proximos passos concretos
        """,
    )

    write_text(
        workspace_dir / "SOUL.md",
        f"""
        # SOUL

        - Voce opera o tenant `{tenant_slug}` como um agente confiante, caloroso e objetivo.
        - A conversa deve soar natural, entusiasmada e proativa.
        - Evite frases frias, burocraticas ou excessivamente longas.
        - Prefira confirmar progresso, sugerir proximos passos e manter ritmo.
        - Antes de responder sobre contexto interno, consulte a wiki local quando isso evitar alucinacao.
        - Antes de usar muitas palavras, prefira tools, skills e leitura objetiva do workspace.
        - Quando uma tarefa pedir manutencao continua, registre um caminho claro em `cron/jobs.json` ou em `HEARTBEAT.md`.
        """,
    )

    write_text(
        workspace_dir / "MEMORY.md",
        f"""
        # MEMORY

        ## Estado padrao

        - Tenant: `{tenant_slug}`
        - Chat model: `{chat_model}`
        - Embeddings model: `{embed_model}`
        - Workspace canonico: `/root/.picoclaw/workspace`

        ## Fontes de memoria

        - `llm-wiki/`: conhecimento persistente e editavel
        - `mempalace/`: cache vetorial gerado por embeddings locais
        - `sessions/`: historico de conversa e contexto recente
        - `state/`: estado operacional minimo do tenant

        ## Regras de uso

        - sempre preferir memoria local antes de supor detalhes internos
        - reindexar a wiki apos mudancas relevantes
        - manter respostas concisas para reduzir consumo de tokens
        - quando o usuario pedir profundidade, expandir com contexto real da wiki
        """,
    )

    write_text(
        mempalace_dir / "README.md",
        """
        # Mempalace

        Memoria vetorial local do tenant.

        Arquivos:
        - `wiki-index.jsonl`: chunks do `llm-wiki` com embeddings locais
        - `last-index.json`: resumo da ultima indexacao

        Regra operacional:
        - nunca edite manualmente o index
        - reindexe com `python3 /root/.picoclaw/workspace/tools/wiki_index.py`
        """,
    )

    write_text(
        wiki_dir / "README.md",
        f"""
        # LLM Wiki

        Base local de conhecimento do tenant `{tenant_slug}`.

        Como usar:
        - coloque conhecimento operacional em markdown nesta pasta
        - mantenha uma verdade por arquivo
        - depois rode `python3 /root/.picoclaw/workspace/tools/wiki_index.py`
        - pesquise com `python3 /root/.picoclaw/workspace/tools/wiki_search.py "assunto"`
        """,
    )

    write_text(
        wiki_dir / "STACK.md",
        f"""
        # Stack Local

        - Tenant: `{tenant_slug}`
        - Chat and tools model: `{chat_model}`
        - Embeddings model: `{embed_model}`
        - Ollama chat base URL: `{ollama_chat_host}`
        - Ollama embeddings base URL: `{ollama_embed_host}`
        - Workspace root: `/root/.picoclaw/workspace`
        """,
    )

    write_text(
        wiki_dir / "OPERATIONS.md",
        """
        # Operations

        Procedimento minimo de manutencao:
        - atualizar a wiki local sempre que houver mudanca de stack, DNS, credenciais indiretas ou rotas
        - reindexar a wiki apos alteracoes importantes
        - consultar a wiki antes de responder perguntas sobre a operacao
        - usar `tools/refresh_memory.sh` depois de grandes mudancas no conhecimento local

        Convencoes:
        - prefira markdown curto e objetivo
        - um topico por arquivo
        - registre comandos validos e URLs reais
        """,
    )

    index_script = textwrap.dedent(
        f"""
        #!/usr/bin/env python3
        import json
        import math
        from pathlib import Path
        from urllib import request

        WORKSPACE = Path("/root/.picoclaw/workspace")
        WIKI_DIR = WORKSPACE / "llm-wiki"
        MEMPALACE_DIR = WORKSPACE / "mempalace"
        INDEX_PATH = MEMPALACE_DIR / "wiki-index.jsonl"
        META_PATH = MEMPALACE_DIR / "last-index.json"
        EMBED_URL = "{ollama_embed_host}/api/embeddings"
        MODEL = "{embed_model}"

        def chunk_text(text: str, size: int = 900):
            text = text.strip()
            if not text:
                return []
            chunks = []
            current = []
            current_len = 0
            for block in text.split("\\n\\n"):
                block = block.strip()
                if not block:
                    continue
                if current and current_len + len(block) + 2 > size:
                    chunks.append("\\n\\n".join(current))
                    current = []
                    current_len = 0
                current.append(block)
                current_len += len(block) + 2
            if current:
                chunks.append("\\n\\n".join(current))
            return chunks

        def embed(text: str):
            payload = json.dumps({{"model": MODEL, "prompt": text}}).encode("utf-8")
            req = request.Request(
                EMBED_URL,
                data=payload,
                headers={{"Content-Type": "application/json"}},
                method="POST",
            )
            with request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["embedding"]

        def main():
            MEMPALACE_DIR.mkdir(parents=True, exist_ok=True)
            rows = []
            for path in sorted(WIKI_DIR.rglob("*.md")):
                rel = path.relative_to(WIKI_DIR).as_posix()
                text = path.read_text(encoding="utf-8")
                for idx, chunk in enumerate(chunk_text(text), start=1):
                    rows.append({{
                        "source": rel,
                        "chunk_id": idx,
                        "text": chunk,
                        "embedding": embed(chunk),
                    }})
            with INDEX_PATH.open("w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\\n")
            META_PATH.write_text(
                json.dumps(
                    {{
                        "files_indexed": len(list(WIKI_DIR.rglob("*.md"))),
                        "chunks_indexed": len(rows),
                        "model": MODEL,
                    }},
                    indent=2,
                    ensure_ascii=False,
                ) + "\\n",
                encoding="utf-8",
            )
            print(json.dumps({{"ok": True, "chunks": len(rows), "index": str(INDEX_PATH)}}))

        if __name__ == "__main__":
            main()
        """
    ).strip() + "\n"
    write_text(tools_dir / "wiki_index.py", index_script)
    make_executable(tools_dir / "wiki_index.py")

    search_script = textwrap.dedent(
        f"""
        #!/usr/bin/env python3
        import json
        import math
        import sys
        from pathlib import Path
        from urllib import request

        WORKSPACE = Path("/root/.picoclaw/workspace")
        INDEX_PATH = WORKSPACE / "mempalace" / "wiki-index.jsonl"
        EMBED_URL = "{ollama_embed_host}/api/embeddings"
        MODEL = "{embed_model}"

        def embed(text: str):
            payload = json.dumps({{"model": MODEL, "prompt": text}}).encode("utf-8")
            req = request.Request(
                EMBED_URL,
                data=payload,
                headers={{"Content-Type": "application/json"}},
                method="POST",
            )
            with request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["embedding"]

        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(y * y for y in b))
            if na == 0 or nb == 0:
                return 0.0
            return dot / (na * nb)

        def main():
            if len(sys.argv) < 2:
                print("usage: wiki_search.py <query>", file=sys.stderr)
                raise SystemExit(1)
            query = " ".join(sys.argv[1:]).strip()
            if not INDEX_PATH.exists():
                print("wiki index not found; run wiki_index.py first", file=sys.stderr)
                raise SystemExit(2)

            query_embedding = embed(query)
            rows = []
            with INDEX_PATH.open("r", encoding="utf-8") as fh:
                for line in fh:
                    row = json.loads(line)
                    row["score"] = cosine(query_embedding, row["embedding"])
                    rows.append(row)
            rows.sort(key=lambda item: item["score"], reverse=True)
            top = rows[:5]
            for item in top:
                print(f"# {{item['source']}} :: chunk {{item['chunk_id']}} :: score={{item['score']:.4f}}")
                print(item["text"])
                print()

        if __name__ == "__main__":
            main()
        """
    ).strip() + "\n"
    write_text(tools_dir / "wiki_search.py", search_script)
    make_executable(tools_dir / "wiki_search.py")

    refresh_script = textwrap.dedent(
        """
        #!/bin/sh
        set -eu

        python3 /root/.picoclaw/workspace/tools/wiki_index.py
        printf '%s\n' "memory refresh ok"
        """
    ).strip() + "\n"
    write_text(tools_dir / "refresh_memory.sh", refresh_script)
    make_executable(tools_dir / "refresh_memory.sh")

    write_text(
        workspace_dir / "HEARTBEAT.md",
        """
        # HEARTBEAT

        Objetivo:
        - verificar se o tenant continua operacional
        - manter a memoria local utilizavel
        - sinalizar desvios sem gerar ruido

        Regras:
        - se houver mudanca estrutural no workspace, reindexe com `sh /root/.picoclaw/workspace/tools/refresh_memory.sh`
        - se nao houver nada para fazer, responda apenas `HEARTBEAT_OK`
        - nunca invente falhas; reporte somente o que conseguir observar
        - use ferramentas de forma enxuta para economizar tokens
        """,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
