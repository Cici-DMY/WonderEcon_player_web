"""API 总路由 — 聚合所有子模块"""
from fastapi import APIRouter

from .init_player import router as init_player_router
from .loan import router as loan_router
from .employment import router as employment_router
from .consumption import router as consumption_router
from .stock import router as stock_router
from .deposit import router as deposit_router
from .player_state import router as player_state_router
from .end_animation import router as end_animation_router

api_router = APIRouter()
api_router.include_router(init_player_router)
api_router.include_router(loan_router)
api_router.include_router(employment_router)
api_router.include_router(consumption_router)
api_router.include_router(stock_router)
api_router.include_router(deposit_router)
api_router.include_router(player_state_router)
api_router.include_router(end_animation_router)
