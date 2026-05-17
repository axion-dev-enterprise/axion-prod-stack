#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import secrets
import sys

import aiohttp


def emit_json(payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False)
    sys.stdout.buffer.write(text.encode("utf-8", "replace") + b"\n")


async def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--origin", default="https://scan.axionenterprise.cloud")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--idle-after-final", type=int, default=8)
    args = parser.parse_args()

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(
            args.url,
            headers={"Authorization": f"Bearer {args.token}", "Origin": args.origin},
            heartbeat=25,
        ) as ws:
            await ws.send_json(
                {
                    "type": "message.send",
                    "id": secrets.token_hex(8),
                    "payload": {"content": args.prompt},
                }
            )
            final_text = None
            events = []
            while True:
                msg = await asyncio.wait_for(ws.receive(), timeout=args.timeout)
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                data = json.loads(msg.data)
                payload = data.get("payload") or {}
                events.append(
                    {
                        "type": data.get("type"),
                        "keys": sorted(payload.keys())[:8],
                        "content": str(payload.get("content", ""))[:180],
                    }
                )
                if data.get("type") in {"message.create", "message.update"} and payload.get("content") and not payload.get("thought"):
                    final_text = payload.get("content")
                if final_text:
                    try:
                        while True:
                            follow = await asyncio.wait_for(ws.receive(), timeout=args.idle_after_final)
                            if follow.type != aiohttp.WSMsgType.TEXT:
                                continue
                            follow_data = json.loads(follow.data)
                            follow_payload = follow_data.get("payload") or {}
                            events.append(
                                {
                                    "type": follow_data.get("type"),
                                    "keys": sorted(follow_payload.keys())[:8],
                                    "content": str(follow_payload.get("content", ""))[:180],
                                }
                            )
                            if (
                                follow_data.get("type") in {"message.create", "message.update"}
                                and follow_payload.get("content")
                                and not follow_payload.get("thought")
                            ):
                                final_text = follow_payload.get("content")
                    except asyncio.TimeoutError:
                        break

    emit_json({"final_text": final_text, "events": events[-20:]})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run()))
    except Exception as exc:
        sys.stderr.buffer.write((json.dumps({"error": str(exc)}, ensure_ascii=False) + "\n").encode("utf-8", "replace"))
        raise
