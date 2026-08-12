"""股票场景 — 3个API路由"""
import sys
import os
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

_CODE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.join(_CODE_DIR, "stock"))
from stock_briefing import build_stock_briefing  # noqa: E402
from apply_stock_decision import apply_stock_decision  # noqa: E402
from stock_market_clearing import run_player_stock_market  # noqa: E402
from config import PLAYER_PATH, ENV_PATH, RESULTS_DIR, text_to_bubbles, read_body  # noqa: E402

router = APIRouter()


@router.post("/api/stock_briefing")
async def stock_briefing():
    try:
        if not os.path.isfile(PLAYER_PATH):
            return JSONResponse(status_code=400, content={"success": False, "error": "player.json not found."})
        with open(PLAYER_PATH, "r", encoding="utf-8") as f:
            player = json.load(f)
        briefing_text = build_stock_briefing(PLAYER_PATH, ENV_PATH)
        bubbles = text_to_bubbles(briefing_text)
        loan_ok = bool(player.get("attributes", {}).get("current_loan_success"))
        return {
            "success": True,
            "matched_agent_id": player["matched_agent_id"],
            "matched_risk": player.get("matched_risk"),
            "loan_forced": loan_ok,
            "briefing_bubbles": bubbles,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/apply_stock_decision")
async def apply_stock_decision_route(request: Request):
    try:
        body = await read_body(request)
        nec_price = int(body["nec_price"])
        lux_price = int(body["lux_price"])
        nec_share = int(body["nec_share"])
        ratio = body.get("ratio")
        ratio = int(ratio) if ratio is not None else None
        seed = body.get("seed", None)
        player = apply_stock_decision(
            nec_price_level=nec_price, lux_price_level=lux_price,
            nec_share_level=nec_share, stock_ratio_level=ratio,
            player_path=PLAYER_PATH, env_path=ENV_PATH, seed=seed,
        )
        result = player.get("stock_decision", {})
        return {"success": True, "decision": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/stock_market_clearing")
async def stock_market_clearing(request: Request):
    try:
        body = await read_body(request)
        seed = body.get("seed", None)
        out = run_player_stock_market(
            player_path=PLAYER_PATH, results_dir=RESULTS_DIR, env_path=ENV_PATH, seed=seed,
        )
        return {"success": True, "narrative": out["narrative"], "result": out["result"]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
