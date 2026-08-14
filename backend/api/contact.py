"""Contact us — POST /api/contact 收集玩家邮箱"""
import re
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from config import read_body
from database.mongo import save_contact

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/api/contact")
async def contact(request: Request):
    try:
        body = await read_body(request)
        email = str(body.get("email", "")).strip()
        if not email:
            return JSONResponse(status_code=400, content={"success": False, "error": "email is required"})
        if not _EMAIL_RE.match(email):
            return JSONResponse(status_code=400, content={"success": False, "error": "invalid email format"})
        save_contact(email)
        return {"success": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})