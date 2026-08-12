"""消费场景 — 3个API路由"""
import sys
import os
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

_CODE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.join(_CODE_DIR, "consumption"))
from consumption_briefing import build_consumption_briefing  # noqa: E402
from apply_consumption_decision import apply_consumption_decision  # noqa: E402
from goods_market_clearing import run_player_goods_market  # noqa: E402
from config import PLAYER_PATH, ENV_PATH, RESULTS_DIR, text_to_bubbles, read_body  # noqa: E402

router = APIRouter()


@router.post("/api/consumption_briefing")
async def consumption_briefing():
    try:
        if not os.path.isfile(PLAYER_PATH):
            return JSONResponse(status_code=400, content={"success": False, "error": "player.json not found."})
        with open(PLAYER_PATH, "r", encoding="utf-8") as f:
            player = json.load(f)
        briefing_text = build_consumption_briefing(PLAYER_PATH, ENV_PATH)
        bubbles = text_to_bubbles(briefing_text)
        return {
            "success": True,
            "matched_agent_id": player["matched_agent_id"],
            "briefing_bubbles": bubbles,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/apply_decision")
async def apply_consumption_decision_route(request: Request):
    try:
        body = await read_body(request)
        nec_price = int(body["nec_price"])
        lux_price = int(body["lux_price"])
        ratio = int(body["ratio"])
        nec_share = int(body["nec_share"])
        seed = body.get("seed", None)
        player = apply_consumption_decision(
            nec_price_level=nec_price, lux_price_level=lux_price,
            consume_ratio_level=ratio, necessity_share_level=nec_share,
            player_path=PLAYER_PATH, env_path=ENV_PATH, seed=seed,
        )
        result = player.get("consumption_decision", {})
        return {"success": True, "decision": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/market_clearing")
async def goods_market_clearing_route(request: Request):
    try:
        body = await read_body(request)
        seed = body.get("seed", None)
        out = run_player_goods_market(player_path=PLAYER_PATH, results_dir=RESULTS_DIR, seed=seed)
        return {"success": True, "narrative": out["narrative"], "result": out["result"]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
