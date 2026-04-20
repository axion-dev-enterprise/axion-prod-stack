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
    data = {
        "agents": {
            "defaults": {
                "workspace": workspace_path,
                "restrict_to_workspace": True,
                "model_name": env("PICOCLAW_DEFAULT_MODEL", "openrouter/xiaomi/mimo-v2-pro"),
                "max_tokens": int(env("PICOCLAW_DEFAULT_MAX_TOKENS", "8192")),
                "context_window": int(env("PICOCLAW_DEFAULT_CONTEXT_WINDOW", "262144")),
                "temperature": 0.2,
                "max_tool_iterations": 12,
                "summarize_message_threshold": 18,
                "summarize_token_percent": 70,
                "tool_feedback": {
                    "enabled": env("PICOCLAW_TOOL_FEEDBACK", "true").lower() == "true",
                    "max_args_length": 300,
                },
            }
        },
        "model_list": [
            {
                "model_name": env("PICOCLAW_DEFAULT_MODEL", "openrouter/xiaomi/mimo-v2-pro"),
                "model": env("PICOCLAW_DEFAULT_MODEL", "openrouter/xiaomi/mimo-v2-pro"),
                "api_key": env("OPENROUTER_API_KEY"),
                "api_base": env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            }
        ],
        "channels": {
            "pico": {
                "enabled": True,
                "token": env("TENANT_ADMIN_TOKEN"),
                "allow_token_query": False,
                "allow_origins": [f"https://{tenant_host}"],
                "allow_from": [],
            }
        },
        "tools": {
            "allow_read_paths": [workspace_path],
            "allow_write_paths": [workspace_path],
            "web": {
                "enabled": True,
                "prefer_native": True,
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
                "enable_deny_patterns": True,
                "custom_deny_patterns": [
                    "rm -rf /",
                    "shutdown",
                    "reboot",
                    "poweroff",
                    "docker ",
                    "docker-compose",
                    "iptables",
                    "ufw ",
                    "mount ",
                    "umount ",
                    "dd if=",
                ],
                "custom_allow_patterns": [
                    "ls",
                    "pwd",
                    "cat",
                    "sed",
                    "awk",
                    "grep",
                    "rg",
                    "find",
                    "python",
                    "python3",
                    "node",
                    "npm",
                    "pnpm",
                    "git",
                    "curl",
                    "wget",
                    "bash",
                    "sh",
                ],
            },
            "append_file": {"enabled": True},
            "edit_file": {"enabled": True},
            "find_skills": {"enabled": False},
            "install_skill": {"enabled": False},
            "list_dir": {"enabled": True},
            "message": {"enabled": True},
            "read_file": {"enabled": True, "mode": "bytes"},
            "spawn": {"enabled": True},
            "subagent": {"enabled": True},
            "web_fetch": {"enabled": True},
            "write_file": {"enabled": True},
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
