"""贷款场景 — 5个API路由"""
import sys
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

_CODE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.join(_CODE_DIR, "loan"))
from loan_briefing import build_loan_briefing  # noqa: E402
from apply_loan_decision import apply_loan_decision  # noqa: E402
from loan_amount_dialogue import build_loan_amount_dialogue  # noqa: E402
from apply_loan_amount import apply_loan_amount  # noqa: E402
from loan_market_clearing import run_player_loan_market  # noqa: E402
from config import ENV_PATH, RESULTS_DIR, text_to_bubbles, read_body, ensure_player_file, load_player_file, require_player_id  # noqa: E402
from database.mongo import save_player, save_decision  # noqa: E402

router = APIRouter()


@router.post("/api/loan_briefing")
async def loan_briefing(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        player = load_player_file(player_path)
        available_tasks = player.get("available_tasks", [])
        eligible = "loan" in available_tasks
        briefing_text = build_loan_briefing(player_path, ENV_PATH)
        bubbles = text_to_bubbles(briefing_text)
        return {
            "success": True,
            "matched_agent_id": player["matched_agent_id"],
            "matched_risk": player.get("matched_risk"),
            "briefing_bubbles": bubbles,
            "eligible": eligible,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/apply_loan_decision")
async def apply_loan_decision_route(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        rate_level = int(body["rate_level"])
        decide_loan = bool(body["decide_loan"])
        seed = body.get("seed", None)
        player = apply_loan_decision(
            rate_level=rate_level, decide_loan=decide_loan,
            player_path=player_path, env_path=ENV_PATH, seed=seed,
        )
        result = player.get("loan_decision", {})
        save_player(player_id, player)
        save_decision(player_id, "apply_loan_decision", {"rate_level": rate_level, "decide_loan": decide_loan}, result)
        return {"success": True, "decision": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/loan_amount_dialogue")
async def loan_amount_dialogue(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        dialogue_text = build_loan_amount_dialogue(player_path, ENV_PATH)
        bubbles = text_to_bubbles(dialogue_text)
        return {"success": True, "bubbles": bubbles}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/apply_loan_amount")
async def apply_loan_amount_route(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        level = int(body["level"])
        seed = body.get("seed", None)
        player = apply_loan_amount(level=level, player_path=player_path, seed=seed)
        result = player.get("loan_amount_decision", {})
        save_player(player_id, player)
        save_decision(player_id, "apply_loan_amount", {"level": level}, result)
        return {"success": True, "decision": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/loan_market_clearing")
async def loan_market_clearing(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        seed = body.get("seed", None)
        out = run_player_loan_market(player_path=player_path, results_dir=RESULTS_DIR, seed=seed)
        save_player(player_id, load_player_file(player_path))
        save_decision(player_id, "loan_market_clearing", None, out.get("result", {}))
        return {"success": True, "narrative": out["narrative"], "result": out.get("result", {})}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})