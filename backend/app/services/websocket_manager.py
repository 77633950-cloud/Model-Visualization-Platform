import asyncio
from typing import Optional
from fastapi import WebSocket
from app.services.event_bus import EventBus


class WebSocketManager:
    """WebSocket 管理器 - 负责实时数据推送"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._active_connections: list[WebSocket] = []
        self._listener_queue: Optional[asyncio.Queue] = None
        self._broadcast_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动 WebSocket 管理器"""
        self._listener_queue = self.event_bus.subscribe()
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def stop(self):
        """停止 WebSocket 管理器"""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        if self._listener_queue:
            self.event_bus.unsubscribe(self._listener_queue)

    async def connect(self, websocket: WebSocket):
        """接受 WebSocket 连接"""
        await websocket.accept()
        self._active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """断开 WebSocket 连接"""
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)

    async def _broadcast_loop(self):
        """广播循环 - 向所有连接推送数据"""
        while True:
            try:
                if self._listener_queue:
                    data = await self._listener_queue.get()
                    disconnected = []
                    for ws in self._active_connections[:]:
                        try:
                            await ws.send_json(data)
                        except Exception:
                            disconnected.append(ws)
                    for ws in disconnected:
                        self.disconnect(ws)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
