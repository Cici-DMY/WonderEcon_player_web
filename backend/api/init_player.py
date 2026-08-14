"""POST /api/init_player — 匹配 agent，生成独立 player_{id}.json 并入库"""
import sys
import os
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine", "match_agent"))
from match_agent import create_player, get_environment_snapshot  # noqa: E402
from config import HOUSEHOLDS_PATH, ENV_PATH, PLAYER_DIR, read_body  # noqa: E402
from database.mongo import save_player  # noqa: E402

router = APIRouter()


@router.post("/api/init_player")
async def init_player(request: Request):
    try:
        body = await read_body(request)
        tick = int(body.get("tick", 6))
        is_labor_force = bool(body.get("is_labor_force", True))
        wealth = int(body.get("wealth", 1))
        risk = str(body.get("risk", "balanced"))

        player_id = str(uuid.uuid4())
        player = create_player(
            selected_tick=tick,
            is_labor_force=is_labor_force,
            wealth_level=wealth,
            risk_preference=risk,
            households_path=HOUSEHOLDS_PATH,
            output_dir=PLAYER_DIR,
            player_filename=f"player_{player_id}.json",
        )

        environment = None
        try:
            environment = get_environment_snapshot(ENV_PATH, tick)
        except Exception:
            pass

        player.pop("_player_json_path", None)
        save_player(player_id, player)

        return {"success": True, "player_id": player_id, "player": player, "environment": environment}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
