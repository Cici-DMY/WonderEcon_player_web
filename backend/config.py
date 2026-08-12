"""共享路径配置和工具函数"""
import json
import os

from fastapi import Request

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.join(_THIS_DIR, "engine")

HOUSEHOLDS_PATH = os.path.join(ENGINE_DIR, "results", "households.json")
ENV_PATH = os.path.join(ENGINE_DIR, "results", "information_environment.json")
RESULTS_DIR = os.path.join(ENGINE_DIR, "results")
PLAYER_DIR = os.path.join(ENGINE_DIR, "match_agent")
PLAYER_PATH = os.path.join(PLAYER_DIR, "player.json")
FRONTEND_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "frontend"))


async def read_body(request: Request) -> dict:
    """安全读取请求 JSON body，空 body 时返回 {}（与原 _read_body 行为一致）。"""
    try:
        body = await request.body()
        if not body:
            return {}
        return json.loads(body)
    except Exception:
        return {}


def text_to_bubbles(text: str) -> list:
    paragraphs = text.split("\n\n")
    bubbles = []
    for para in paragraphs:
        t = para.strip()
        if t:
            bubbles.append({"role": "npc", "text": t})
    return bubbles
