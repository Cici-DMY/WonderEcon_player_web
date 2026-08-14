"""就业场景 — 3个API路由"""
import sys
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

_CODE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.join(_CODE_DIR, "employment"))
from employment_briefing import build_employment_briefing  # noqa: E402
from apply_employment_decision import apply_employment_decision  # noqa: E402
from labor_market_clearing import run_player_labor_market  # noqa: E402
from config import ENV_PATH, RESULTS_DIR, text_to_bubbles, read_body, ensure_player_file, load_player_file, require_player_id  # noqa: E402
from database.mongo import save_player, save_decision  # noqa: E402

router = APIRouter()


@router.post("/api/employment_briefing")
async def employment_briefing(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        player = load_player_file(player_path)
        briefing_text = build_employment_briefing(player_path, ENV_PATH)
        bubbles = text_to_bubbles(briefing_text)
        is_employed = bool(player.get("attributes", {}).get("is_employed"))
        return {
            "success": True,
            "matched_agent_id": player["matched_agent_id"],
            "is_employed": is_employed,
            "briefing_bubbles": bubbles,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/apply_employment_decision")
async def apply_employment_decision_route(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        wage_level = int(body["wage_level"])
        quit_job = bool(body.get("quit", False))
        seed = body.get("seed", None)
        player = apply_employment_decision(
            wage_level=wage_level, quit=quit_job,
            player_path=player_path, env_path=ENV_PATH, seed=seed,
        )
        result = player.get("employment_decision", {})
        save_player(player_id, player)
        save_decision(player_id, "apply_employment_decision", {"wage_level": wage_level, "quit": quit_job}, result)
        return {"success": True, "decision": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/labor_market_clearing")
async def labor_market_clearing(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        seed = body.get("seed", None)
        out = run_player_labor_market(player_path=player_path, results_dir=RESULTS_DIR, seed=seed)
        save_player(player_id, load_player_file(player_path))
        save_decision(player_id, "labor_market_clearing", None, out.get("result", {}))
        return {
            "success": True,
            "narrative": out["narrative"],
            "outcome": out.get("outcome", ""),
            "result": out.get("result", {}),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})