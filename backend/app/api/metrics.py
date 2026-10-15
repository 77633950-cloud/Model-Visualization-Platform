from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.services.event_bus import EventBus
from app.db.database import get_db

router = APIRouter(prefix="/api")
event_bus: Optional[EventBus] = None


def init_metrics_router(bus: EventBus):
    """初始化指标路由"""
    global event_bus
    event_bus = bus
    return router


@router.get("/metrics/overview")
async def get_overview(minutes: int = Query(default=5, ge=1, le=1440), db: AsyncSession = Depends(get_db)):
    """获取概览指标"""
    if event_bus is None:
        return {"error": "服务未初始化"}
    return event_bus.get_overview(minutes=minutes)


@router.get("/metrics/timeseries")
async def get_timeseries(
    minutes: int = Query(default=60, ge=1, le=10080),
    model: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """获取时间序列数据"""
    if event_bus is None:
        return {"error": "服务未初始化"}
    return {"data": event_bus.get_timeseries(minutes=minutes, model=model)}


@router.get("/errors/top")
async def get_top_errors(limit: int = Query(default=10, ge=1, le=100)):
    """获取热门错误"""
    if event_bus is None:
        return {"error": "服务未初始化"}
    return {"errors": event_bus.get_top_errors(limit=limit)}


@router.get("/errors/recent")
async def get_recent_errors(limit: int = Query(default=20, ge=1, le=100)):
    """获取最近错误"""
    if event_bus is None:
        return {"error": "服务未初始化"}
    return {"errors": event_bus.get_recent_errors(limit=limit)}
