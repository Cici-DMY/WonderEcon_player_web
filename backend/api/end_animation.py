"""结算动画 — POST /api/end_animation"""
import sys
import os
import json
import re as _re
import hashlib as _hashlib
import shutil as _shutil
from datetime import datetime as _dt
from fastapi import APIRouter
from fastapi.responses import JSONResponse

_CODE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.join(_CODE_DIR, "decision_review"))
sys.path.insert(0, os.path.join(_CODE_DIR, "asset_happiness"))
sys.path.insert(0, os.path.join(_CODE_DIR, "EPTI"))
from decision_review import build_decision_review  # noqa: E402
from compare_performance import compare_performance  # noqa: E402
from judge_epti import judge_player_epti  # noqa: E402
from config import PLAYER_PATH, RESULTS_DIR, FRONTEND_DIR  # noqa: E402

router = APIRouter()


@router.post("/api/end_animation")
async def end_animation():
    try:
        if not os.path.isfile(PLAYER_PATH):
            return JSONResponse(status_code=400, content={"success": False, "error": "player.json not found."})

        end_dir = os.path.join(FRONTEND_DIR, "modules", "interaction", "end-animation")
        template_path = os.path.join(end_dir, "game_end_animation.html")
        output_path = os.path.join(end_dir, "game_end_animation_live.html")
        player_save_dir = os.path.normpath(
            os.path.join(FRONTEND_DIR, "modules", "interaction", "player-information")
        )

        with open(PLAYER_PATH, "rb") as f:
            content = f.read()
        content_hash = _hashlib.sha256(content).hexdigest()[:8]
        mtime = os.path.getmtime(PLAYER_PATH)
        time_tag = _dt.fromtimestamp(mtime).strftime("%Y%m%d_%H%M%S")
        filename = f"{time_tag}_{content_hash}.json"
        save_path = os.path.join(player_save_dir, filename)
        os.makedirs(player_save_dir, exist_ok=True)
        if not os.path.exists(save_path):
            _shutil.copy2(PLAYER_PATH, save_path)

        review = build_decision_review(PLAYER_PATH)
        perf = compare_performance(PLAYER_PATH, RESULTS_DIR)
        epti = judge_player_epti(PLAYER_PATH, RESULTS_DIR)

        with open(template_path, "r", encoding="utf-8") as f:
            html = f.read()

        def _inject(h, placeholder, data):
            pattern = r'/\*\[\[' + _re.escape(placeholder) + r'\]\]\*/(null|\[\]|\{\})'
            replacement = json.dumps(data, ensure_ascii=False)
            return _re.sub(pattern, replacement, h)

        html = _inject(html, "DECISION_REVIEW_LINES", review["lines"])
        html = _inject(html, "COMPARE_PERFORMANCE", perf)
        html = _inject(html, "EPTI_DATA", epti)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        rel_path = "modules/interaction/end-animation/game_end_animation_live.html"
        return {"success": True, "url": rel_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
