"""玩家状态查询"""
import os
import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from config import PLAYER_PATH

router = APIRouter()


@router.post("/api/player_state")
async def player_state():
    try:
        if not os.path.isfile(PLAYER_PATH):
            return JSONResponse(status_code=404, content={"success": False, "error": "player.json not found"})
        with open(PLAYER_PATH, "r", encoding="utf-8") as f:
            player = json.load(f)
        return {"success": True, "player": player}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
