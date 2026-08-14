"""消费场景 — 3个API路由"""
import sys
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

_CODE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.join(_CODE_DIR, "consumption"))
from consumption_briefing import build_consumption_briefing  # noqa: E402
from apply_consumption_decision import apply_consumption_decision  # noqa: E402
from goods_market_clearing import run_player_goods_market  # noqa: E402
from config import ENV_PATH, RESULTS_DIR, text_to_bubbles, read_body, ensure_player_file, load_player_file, require_player_id  # noqa: E402
from database.mongo import save_player, save_decision  # noqa: E402

router = APIRouter()


@router.post("/api/consumption_briefing")
async def consumption_briefing(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        player = load_player_file(player_path)
        briefing_text = build_consumption_briefing(player_path, ENV_PATH)
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
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        nec_price = int(body["nec_price"])
        lux_price = int(body["lux_price"])
        ratio = int(body["ratio"])
        nec_share = int(body["nec_share"])
        seed = body.get("seed", None)
        player = apply_consumption_decision(
            nec_price_level=nec_price, lux_price_level=lux_price,
            consume_ratio_level=ratio, necessity_share_level=nec_share,
            player_path=player_path, env_path=ENV_PATH, seed=seed,
        )
        result = player.get("consumption_decision", {})
        save_player(player_id, player)
        save_decision(player_id, "apply_decision", {"nec_price": nec_price, "lux_price": lux_price, "ratio": ratio, "nec_share": nec_share}, result)
        return {"success": True, "decision": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/market_clearing")
async def goods_market_clearing_route(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        seed = body.get("seed", None)
        out = run_player_goods_market(player_path=player_path, results_dir=RESULTS_DIR, seed=seed)
        save_player(player_id, load_player_file(player_path))
        save_decision(player_id, "market_clearing", None, out["result"])
        return {"success": True, "narrative": out["narrative"], "result": out["result"]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})