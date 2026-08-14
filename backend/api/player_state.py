"""玩家状态查询"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from config import read_body, ensure_player_file, load_player_file, require_player_id

router = APIRouter()


@router.post("/api/player_state")
async def player_state(request: Request):
    try:
        body = await read_body(request)
        player_id, err = require_player_id(body)
        if err:
            return err
        player_path = ensure_player_file(player_id)
        player = load_player_file(player_path)
        return {"success": True, "player": player}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})