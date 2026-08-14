"""共享路径配置和工具函数"""
import json
import os

from fastapi import Request
from fastapi.responses import JSONResponse

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.join(_THIS_DIR, "engine")

HOUSEHOLDS_PATH = os.path.join(ENGINE_DIR, "results", "households.json")
ENV_PATH = os.path.join(ENGINE_DIR, "results", "information_environment.json")
RESULTS_DIR = os.path.join(ENGINE_DIR, "results")
PLAYER_DIR = os.path.join(ENGINE_DIR, "match_agent")
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


def get_player_path(player_id: str) -> str:
    """返回某玩家的独立 player 文件路径：PLAYER_DIR/player_{player_id}.json"""
    return os.path.join(PLAYER_DIR, f"player_{player_id}.json")


def ensure_player_file(player_id: str) -> str:
    """确保玩家文件存在；若磁盘丢失（Render 重启/休眠），从 MongoDB 恢复后返回路径。"""
    path = get_player_path(player_id)
    if not os.path.isfile(path):
        from database.mongo import load_player
        state = load_player(player_id)
        if state is None:
            raise FileNotFoundError(f"Player {player_id} not found")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    return path


def load_player_file(player_path: str) -> dict:
    """读取玩家 JSON 文件为 dict。"""
    with open(player_path, "r", encoding="utf-8") as f:
        return json.load(f)


def require_player_id(body: dict):
    """从请求 body 提取 player_id；缺失时返回 (None, 400 JSONResponse)，否则 (player_id, None)。"""
    player_id = body.get("player_id")
    if not player_id:
        return None, JSONResponse(status_code=400, content={"success": False, "error": "player_id is required"})
    return str(player_id), None


def text_to_bubbles(text: str) -> list:
    paragraphs = text.split("\n\n")
    bubbles = []
    for para in paragraphs:
        t = para.strip()
        if t:
            bubbles.append({"role": "npc", "text": t})
    return bubbles
