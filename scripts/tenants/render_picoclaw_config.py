#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: render_picoclaw_config.py <tenant-slug> <tenant-host> <output-path>", file=sys.stderr)
        return 1

    tenant_slug, tenant_host, output_path = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    workspace_path = "/root/.picoclaw/workspace"
    provider = env("FLOW_LLM_PROVIDER", "openrouter").strip().lower()
    model_name = env("PICOCLAW_DEFAULT_MODEL", "openrouter/xiaomi/mimo-v2-pro")
    upstream_model = env("PICOCLAW_UPSTREAM_MODEL", model_name)
    api_base = env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = env("OPENROUTER_API_KEY")

    if provider == "cloudflare":
        cf_account_id = env("CF_ACCOUNT_ID")
        model_name = env("PICOCLAW_DEFAULT_MODEL", "cloudflare/llama")
        upstream_model = env("PICOCLAW_UPSTREAM_MODEL", "@cf/meta/llama-3.1-8b-instruct")
        api_base = env(
            "CF_WORKERS_AI_BASE_URL",
            f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id}/ai/v1" if cf_account_id else "",
        )
        api_key = env("CF_API_TOKEN")
    elif provider == "openai":
        model_name = env("PICOCLAW_DEFAULT_MODEL", "gpt-4o")
        upstream_model = env("PICOCLAW_UPSTREAM_MODEL", model_name)
        api_base = env("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = env("OPENAI_API_KEY")
    elif provider == "ollama":
        model_name = env("PICOCLAW_DEFAULT_MODEL", "local/qwen2.5:1.5b")
        upstream_model = env("PICOCLAW_UPSTREAM_MODEL", "qwen2.5:1.5b")
        api_base = env("OLLAMA_CHAT_BASE_URL", "http://ollama-openai-proxy:8021/v1")
        api_key = env("OLLAMA_API_KEY", "ollama-local")
    request_timeout = int(env("PICOCLAW_REQUEST_TIMEOUT", "300" if provider == "ollama" else "0"))
    enable_whatsapp = env("PICOCLAW_ENABLE_WHATSAPP", "true").lower() == "true"

    channel_list = {
        "pico": {
            "enabled": True,
            "token": env("TENANT_ADMIN_TOKEN"),
            "type": "pico",
            "settings": {
                "token": env("TENANT_ADMIN_TOKEN"),
                "allow_token_query": False,
                "allow_origins": [
                    f"https://{tenant_host}",
                    env("FLOW_PUBLIC_URL", "https://flow.axionenterprise.cloud"),
                    env("TENANT_CHAT_SCAN_ORIGIN", "https://scan.axionenterprise.cloud"),
                    env("TENANT_CHAT_PUBLIC_ORIGIN", "http://203.161.39.174:8010"),
                ],
                "allow_from": [],
                "ping_interval": 30,
                "read_timeout": 60,
                "max_connections": 100,
            },
        }
    }
    if enable_whatsapp:
        channel_list["whatsapp"] = {
            "enabled": True,
            "type": "whatsapp_native",
            "settings": {
                "use_native": True,
                "session_store_path": env("PICOCLAW_WHATSAPP_SESSION_STORE", "/root/.picoclaw/whatsapp_session"),
            },
        }

    data = {
        "session": {
            "dimensions": ["chat"],
        },
        "version": 3,
        "isolation": {},
        "agents": {
            "defaults": {
                "workspace": workspace_path,
                "restrict_to_workspace": True,
                "allow_read_outside_workspace": False,
                "model_name": model_name,
                "max_tokens": int(env("PICOCLAW_DEFAULT_MAX_TOKENS", "8192")),
                "context_window": int(env("PICOCLAW_DEFAULT_CONTEXT_WINDOW", "262144")),
                "temperature": 0.2,
                "max_tool_iterations": 12,
                "summarize_message_threshold": 18,
                "summarize_token_percent": 70,
                "steering_mode": "one-at-a-time",
                "split_on_marker": False,
                "tool_feedback": {
                    "enabled": env("PICOCLAW_TOOL_FEEDBACK", "true").lower() == "true",
                    "max_args_length": 300,
                },
            }
        },
        "model_list": [
            {
                "model_name": model_name,
                "model": upstream_model,
                "api_key": api_key,
                "api_keys": [api_key] if api_key else [],
                "api_base": api_base,
                "request_timeout": request_timeout,
            }
        ],
        "channel_list": channel_list,
        "tools": {
            "allow_read_paths": ["/"],
            "allow_write_paths": ["/"],
            "filter_sensitive_data": True,
            "filter_min_length": 8,
            "web": {
                "enabled": env("PICOCLAW_WEB_ENABLED", "false").lower() == "true",
                "prefer_native": env("PICOCLAW_WEB_PREFER_NATIVE", "false").lower() == "true",
                "provider": env("PICOCLAW_WEB_PROVIDER", "auto"),
                "private_host_whitelist": [],
                "brave": {
                    "enabled": bool(env("BRAVE_API_KEY")),
                    "api_key": env("BRAVE_API_KEY"),
                    "max_results": 5,
                },
                "tavily": {
                    "enabled": bool(env("TAVILY_API_KEY")),
                    "api_key": env("TAVILY_API_KEY"),
                    "max_results": 5,
                },
            },
            "cron": {
                "enabled": True,
                "exec_timeout_minutes": 120,
                "allow_command": True,
                "allow_external_channels": True,
                "allow_public_channels": True,
                "allow_non_internal_channels": True,
            },
            "mcp": {
                "enabled": env("PICOCLAW_ENABLE_MCP", "false").lower() == "true",
                "discovery": {
                    "enabled": False,
                    "ttl": 5,
                    "max_search_results": 5,
                    "use_bm25": True,
                    "use_regex": False,
                },
                "servers": {},
            },
            "exec": {
                "enabled": env("PICOCLAW_ENABLE_EXEC", "true").lower() == "true",
                "enable_deny_patterns": False,
                "allow_remote": True,
                "custom_deny_patterns": [],
                "custom_allow_patterns": [".*"],
                "timeout_seconds": 3600,
            },
            "skills": {
                "enabled": True,
                "registries": {
                    "clawhub": {
                        "base_url": "https://clawhub.ai",
                        "enabled": True,
                    },
                    "github": {
                        "base_url": "https://github.com",
                        "enabled": True,
                    },
                },
                "github": {},
                "max_concurrent_searches": 2,
                "search_cache": {
                    "max_size": 50,
                    "ttl_seconds": 300,
                },
            },
            "media_cleanup": {
                "enabled": True,
                "max_age_minutes": 30,
                "interval_minutes": 5,
            },
            "append_file": {"enabled": True},
            "edit_file": {"enabled": True},
            "find_skills": {"enabled": False},
            "install_skill": {"enabled": False},
            "list_dir": {"enabled": True},
            "message": {"enabled": True},
            "read_file": {"enabled": True, "mode": "bytes", "max_read_file_size": 10485760},
            "send_file": {"enabled": True},
            "send_tts": {"enabled": False},
            "spawn": {"enabled": True},
            "spawn_status": {"enabled": False},
            "i2c": {"enabled": False},
            "spi": {"enabled": False},
            "subagent": {"enabled": True},
            "web_fetch": {"enabled": True},
            "write_file": {"enabled": True, "allow_overwrite": True},
        },
        "heartbeat": {"enabled": True, "interval": 30},
        "hooks": {
            "enabled": True,
            "defaults": {
                "observer_timeout_ms": 500,
                "interceptor_timeout_ms": 5000,
                "approval_timeout_ms": 60000,
            },
        },
        "gateway": {
            "host": "0.0.0.0",
            "port": int(env("PICOCLAW_GATEWAY_PORT", "18790")),
            "hot_reload": False,
            "log_level": "info",
        },
        "tenant": {
            "slug": tenant_slug,
            "host": tenant_host,
            "flow_public_url": env("FLOW_PUBLIC_URL", "https://flow.axionenterprise.cloud"),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
