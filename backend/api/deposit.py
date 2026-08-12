"""存款场景 — 3个API路由"""
import sys
import os
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

_CODE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.join(_CODE_DIR, "deposit"))
from deposit_briefing import build_deposit_briefing  # noqa: E402
from apply_deposit_decision import apply_deposit_decision  # noqa: E402
from deposit_market_clearing import run_player_deposit_market  # noqa: E402
from config import PLAYER_PATH, ENV_PATH, RESULTS_DIR, text_to_bubbles, read_body  # noqa: E402

router = APIRouter()


@router.post("/api/deposit_briefing")
async def deposit_briefing():
    try:
        if not os.path.isfile(PLAYER_PATH):
            return JSONResponse(status_code=400, content={"success": False, "error": "player.json not found."})
        with open(PLAYER_PATH, "r", encoding="utf-8") as f:
            player = json.load(f)
        briefing_text = build_deposit_briefing(PLAYER_PATH, ENV_PATH)
        bubbles = text_to_bubbles(briefing_text)
        return {
            "success": True,
            "matched_agent_id": player["matched_agent_id"],
            "briefing_bubbles": bubbles,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/apply_deposit_decision")
async def apply_deposit_decision_route(request: Request):
    try:
        body = await read_body(request)
        level = int(body["level"])
        seed = body.get("seed", None)
        player = apply_deposit_decision(level=level, player_path=PLAYER_PATH, env_path=ENV_PATH, seed=seed)
        result = player.get("deposit_decision", {})
        return {"success": True, "decision": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/deposit_market_clearing")
async def deposit_market_clearing(request: Request):
    try:
        body = await read_body(request)
        seed = body.get("seed", None)
        out = run_player_deposit_market(player_path=PLAYER_PATH, results_dir=RESULTS_DIR, seed=seed)
        return {"success": True, "narrative": out["narrative"], "result": out.get("result", {})}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
