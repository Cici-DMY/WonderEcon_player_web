"""WonderEcon MongoDB 接口层（Atlas 云端持久化）

三个集合：
- players:   每个玩家的完整状态（player_id 唯一索引）
- decisions: 每次决策记录
- contacts:  落地页 Contact us 收集的邮箱

连接串通过环境变量 MONGODB_URI 注入。未设置时抛错（本地无数据库场景）。
"""
import os
from datetime import datetime, timezone

from pymongo import MongoClient

MONGODB_URI = os.environ.get("MONGODB_URI", "")
DB_NAME = "wonderecon"

_client = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db():
    """懒加载 MongoClient，缓存连接。"""
    global _client
    if _client is None:
        if not MONGODB_URI:
            raise RuntimeError("MONGODB_URI environment variable is not set")
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    return _client[DB_NAME]


def _clean_state(state: dict) -> dict:
    """剔除 machine-specific 的临时字段（如 _player_json_path）。"""
    return {k: v for k, v in state.items() if k != "_player_json_path"}


def save_player(player_id: str, state: dict) -> None:
    """upsert 玩家状态。created_at / consent 仅在首次插入时写入。"""
    db = get_db()
    doc = {
        "player_id": player_id,
        "matched_agent_id": state.get("matched_agent_id"),
        "is_labor_force": state.get("is_labor_force"),
        "wealth_level": state.get("wealth_level"),
        "risk_preference": state.get("risk_preference"),
        "state": _clean_state(state),
        "updated_at": _now(),
    }
    db.players.update_one(
        {"player_id": player_id},
        {"$set": doc, "$setOnInsert": {"created_at": _now(), "consent": _now()}},
        upsert=True,
    )


def load_player(player_id: str):
    """读取玩家状态，不存在返回 None。"""
    db = get_db()
    doc = db.players.find_one({"player_id": player_id})
    return doc.get("state") if doc else None


def save_decision(player_id: str, decision_type: str, params=None, result=None) -> None:
    """保存一次决策记录。"""
    db = get_db()
    db.decisions.insert_one({
        "player_id": player_id,
        "decision_type": decision_type,
        "params": params,
        "result": result,
        "created_at": _now(),
    })


def save_contact(email: str) -> None:
    """保存 Contact us 邮箱。"""
    db = get_db()
    db.contacts.insert_one({"email": email, "created_at": _now()})


def ensure_indexes() -> None:
    """建索引（幂等）。"""
    db = get_db()
    db.players.create_index("player_id", unique=True)
    db.decisions.create_index("player_id")
    db.contacts.create_index("email")
