"""存款场景 — 3个API路由"""
import sys
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

_CODE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.join(_CODE_DIR, "deposit"))
from deposit_briefing import build_deposit_briefing  # noqa: E402
from apply_deposit_decision import apply_deposit_decision  # noqa: E402
from deposit_market_clearing import run_player_deposit_market  # noqa: E402
from config import ENV_PATH, RESULTS_DIR, text_to_bubbles, read_body, ensure_player_file, load_player_file, require_player_id  # noqa: E402
from database.mongo import save_player, save_decision  # noqa: E402

router = APIRouter()


@router.post("/api/deposit_briefing")
async def deposit_briefing(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        player = load_player_file(player_path)
        briefing_text = build_deposit_briefing(player_path, ENV_PATH)
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
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        level = int(body["level"])
        seed = body.get("seed", None)
        player = apply_deposit_decision(level=level, player_path=player_path, env_path=ENV_PATH, seed=seed)
        result = player.get("deposit_decision", {})
        save_player(player_id, player)
        save_decision(player_id, "apply_deposit_decision", {"level": level}, result)
        return {"success": True, "decision": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/deposit_market_clearing")
async def deposit_market_clearing(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        seed = body.get("seed", None)
        out = run_player_deposit_market(player_path=player_path, results_dir=RESULTS_DIR, seed=seed)
        save_player(player_id, load_player_file(player_path))
        save_decision(player_id, "deposit_market_clearing", None, out.get("result", {}))
        return {"success": True, "narrative": out["narrative"], "result": out.get("result", {})}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})