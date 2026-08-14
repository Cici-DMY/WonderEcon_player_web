"""
WonderEcon Player Mode — FastAPI 后端入口
==========================================
路由定义在 api/ 子模块中，main.py 仅负责应用组装和静态文件服务。

启动：python main.py  或  uvicorn main:app --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.router import api_router
from config import FRONTEND_DIR

ROUTES = [
    "/api/init_player",
    "/api/loan_briefing", "/api/apply_loan_decision", "/api/loan_amount_dialogue",
    "/api/apply_loan_amount", "/api/loan_market_clearing",
    "/api/employment_briefing", "/api/apply_employment_decision", "/api/labor_market_clearing",
    "/api/consumption_briefing", "/api/apply_decision", "/api/market_clearing",
    "/api/stock_briefing", "/api/apply_stock_decision", "/api/stock_market_clearing",
    "/api/deposit_briefing", "/api/apply_deposit_decision", "/api/deposit_market_clearing",
    "/api/player_state", "/api/end_animation", "/api/contact",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[WonderEcon API] {len(ROUTES)} routes ready on http://0.0.0.0:8000")
    for r in ROUTES:
        print(f"  POST {r}")
    yield


app = FastAPI(title="WonderEcon Player API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
