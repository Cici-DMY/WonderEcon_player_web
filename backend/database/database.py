"""
WonderEcon 数据库接口层（第一阶段：SQLite）
===========================================
与 player.json 并行工作，后续可平滑切换为唯一数据源。

用法：
    from database.database import create_player, get_player_state, save_decision, save_state
"""
import sqlite3
import json
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wonderecon.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matched_agent_id INTEGER,
                is_labor_force INTEGER,
                wealth_level INTEGER,
                risk_preference TEXT,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                decision_type TEXT NOT NULL,
                params_json TEXT,
                result_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players(id)
            )
        """)
    return DB_PATH


def create_player(player_data):
    """创建新玩家记录，返回 player_id。player_data 为完整的 player 字典。"""
    now = datetime.now(timezone.utc).isoformat()
    attrs = player_data.get("attributes", {})
    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO players (matched_agent_id, is_labor_force, wealth_level, risk_preference,
               state_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                player_data.get("matched_agent_id"),
                1 if player_data.get("is_labor_force") else 0,
                player_data.get("wealth_level"),
                player_data.get("risk_preference"),
                json.dumps(player_data, ensure_ascii=False),
                now,
                now,
            ),
        )
        return cur.lastrowid


def get_player_state(player_id: int = None):
    """读取玩家状态。不传 player_id 时返回最新一条。"""
    with _get_conn() as conn:
        if player_id:
            row = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        else:
            row = conn.execute("SELECT * FROM players ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return json.loads(row["state_json"])


def save_decision(player_id: int, decision_type: str, params=None, result=None):
    """保存一次决策记录，返回 decision_id。"""
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO decisions (player_id, decision_type, params_json, result_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                player_id,
                decision_type,
                json.dumps(params, ensure_ascii=False) if params else None,
                json.dumps(result, ensure_ascii=False) if result else None,
                now,
            ),
        )
        return cur.lastrowid


def save_state(player_id: int, player_data: dict) -> None:
    """更新玩家状态。"""
    now = datetime.now(timezone.utc).isoformat()
    attrs = player_data.get("attributes", {})
    with _get_conn() as conn:
        conn.execute(
            """UPDATE players SET
               matched_agent_id = ?, is_labor_force = ?, wealth_level = ?,
               risk_preference = ?, state_json = ?, updated_at = ?
               WHERE id = ?""",
            (
                player_data.get("matched_agent_id"),
                1 if player_data.get("is_labor_force") else 0,
                player_data.get("wealth_level"),
                player_data.get("risk_preference"),
                json.dumps(player_data, ensure_ascii=False),
                now,
                player_id,
            ),
        )


def list_decisions(player_id, decision_type=None):
    """列出某玩家的决策历史。"""
    with _get_conn() as conn:
        if decision_type:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE player_id = ? AND decision_type = ? ORDER BY id DESC",
                (player_id, decision_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE player_id = ? ORDER BY id DESC", (player_id,)
            ).fetchall()
        return [
            {
                "id": r["id"],
                "decision_type": r["decision_type"],
                "params": json.loads(r["params_json"]) if r["params_json"] else None,
                "result": json.loads(r["result_json"]) if r["result_json"] else None,
                "created_at": r["created_at"],
            }
            for r in rows
        ]


# 模块加载时自动初始化
_init_db()
