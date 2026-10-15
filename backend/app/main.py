from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from app.db.database import init_db
from app.services.event_bus import EventBus
from app.services.websocket_manager import WebSocketManager
from app.proxy.proxy_router import init_proxy_router
from app.api.metrics import init_metrics_router

event_bus = EventBus(window_seconds=settings.METRICS_WINDOW_SECONDS)
ws_manager = WebSocketManager(event_bus)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    await init_db()
    await event_bus.start()
    await ws_manager.start()

    scheduler.add_job(
        event_bus.cleanup_old_data,
        "interval",
        days=1,
        args=[settings.DATA_RETENTION_DAYS],
    )
    scheduler.start()

    yield

    await ws_manager.stop()
    await event_bus.stop()
    scheduler.shutdown()


app = FastAPI(title="模型可视化平台", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(init_proxy_router(event_bus))
app.include_router(init_metrics_router(event_bus))


# 【修复1】WebSocket 端点必须用 @app.websocket 而不是 @app.get
@app.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 状态端点"""
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "正常"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
