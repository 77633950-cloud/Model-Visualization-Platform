import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional
from app.models.schemas import RequestEvent, MetricRollup, ModelHealth, TimeSeriesPoint


class EventBus:
    """事件总线类 - 负责事件收集、聚合和分发"""
    
    def __init__(self, window_seconds: int = 5):
        self.window_seconds = window_seconds
        self._queue: asyncio.Queue[RequestEvent] = asyncio.Queue()
        self._events: list[RequestEvent] = []
        self._rollups: list[MetricRollup] = []
        self._model_health: dict[str, ModelHealth] = {}
        self._listeners: list[asyncio.Queue] = []
        self._worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """启动事件总线"""
        self._worker_task = asyncio.create_task(self._aggregation_worker())

    async def stop(self):
        """停止事件总线"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def push_event(self, event: RequestEvent):
        """推送事件到队列"""
        await self._queue.put(event)
        async with self._lock:
            self._events.append(event)
            self._update_model_health(event)

    def subscribe(self) -> asyncio.Queue:
        """订阅事件更新"""
        q: asyncio.Queue = asyncio.Queue()
        self._listeners.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """取消订阅"""
        if q in self._listeners:
            self._listeners.remove(q)

    async def _notify_listeners(self, data: dict):
        """通知所有监听器"""
        for q in self._listeners[:]:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                pass

    def _update_model_health(self, event: RequestEvent):
        """更新模型健康状态"""
        now = datetime.utcnow()
        if event.model not in self._model_health:
            self._model_health[event.model] = ModelHealth(
                model=event.model, is_available=True, last_ok_at=now
            )

        health = self._model_health[event.model]
        if event.status == "success":
            health.is_available = True
            health.last_ok_at = now
            health.degraded_reason = None
        else:
            if event.error_type and "timeout" in event.error_type.lower():
                health.degraded_reason = "超时"
            elif event.error_type and "5" in event.error_type:
                health.degraded_reason = "服务器错误"
            else:
                health.degraded_reason = event.error_type
            health.is_available = False

    async def _aggregation_worker(self):
        """聚合工作器 - 定时计算指标"""
        while True:
            try:
                await asyncio.sleep(self.window_seconds)
                await self._compute_rollups()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _compute_rollups(self):
        """计算指标聚合"""
        async with self._lock:
            if not self._events:
                return

            now = datetime.utcnow()
            window_start = now - timedelta(seconds=self.window_seconds)
            recent = [e for e in self._events if e.timestamp >= window_start]
            self._events = [e for e in self._events if e.timestamp >= window_start - timedelta(seconds=60)]

            model_groups: dict[str, list[RequestEvent]] = defaultdict(list)
            for e in recent:
                model_groups[e.model].append(e)

            new_rollups = []
            for model, events in model_groups.items():
                total = len(events)
                success = sum(1 for e in events if e.status == "success")
                errors = total - success
                latencies = sorted([e.latency_ms for e in events])
                p95_idx = max(0, int(len(latencies) * 0.95) - 1)
                p95 = latencies[p95_idx] if latencies else 0.0

                rollup = MetricRollup(
                    window_start=now,
                    model=model,
                    qps=total / self.window_seconds,
                    success_rate=success / total if total > 0 else 0.0,
                    p95_latency=p95,
                    error_rate=errors / total if total > 0 else 0.0,
                )
                new_rollups.append(rollup)

            self._rollups.extend(new_rollups)
            max_rollups = 86400 // self.window_seconds * 7
            if len(self._rollups) > max_rollups:
                self._rollups = self._rollups[-max_rollups:]

            await self._notify_listeners({
                "type": "timeseries_update",
                "rollups": [r.model_dump() for r in new_rollups],
                "model_health": [h.model_dump() for h in self._model_health.values()],
            })

    def get_overview(self, minutes: int = 5) -> dict:
        """获取概览指标"""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=minutes)
        recent = [e for e in self._events if e.timestamp >= cutoff]

        if not recent:
            return {
                "qps": 0.0,
                "success_rate": 0.0,
                "p50_latency": 0.0,
                "p95_latency": 0.0,
                "error_rate": 0.0,
                "model_health": [h.model_dump() for h in self._model_health.values()],
            }

        total = len(recent)
        success = sum(1 for e in recent if e.status == "success")
        errors = total - success
        latencies = sorted([e.latency_ms for e in recent])
        p50_idx = max(0, int(len(latencies) * 0.5) - 1)
        p95_idx = max(0, int(len(latencies) * 0.95) - 1)

        return {
            "qps": total / (minutes * 60),
            "success_rate": success / total if total > 0 else 0.0,
            "p50_latency": latencies[p50_idx] if latencies else 0.0,
            "p95_latency": latencies[p95_idx] if latencies else 0.0,
            "error_rate": errors / total if total > 0 else 0.0,
            "model_health": [h.model_dump() for h in self._model_health.values()],
        }

    def get_timeseries(self, minutes: int = 60, model: Optional[str] = None) -> list[dict]:
        """获取时间序列数据"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        rollups = [r for r in self._rollups if r.window_start >= cutoff]
        if model:
            rollups = [r for r in rollups if r.model == model]
        return [r.model_dump() for r in rollups]

    def get_top_errors(self, limit: int = 10) -> list[dict]:
        """获取热门错误"""
        error_counts: dict[str, int] = defaultdict(int)
        error_last_seen: dict[str, datetime] = {}
        for e in self._events:
            if e.error_type:
                error_counts[e.error_type] += 1
                error_last_seen[e.error_type] = max(
                    error_last_seen.get(e.error_type, e.timestamp), e.timestamp
                )

        errors = [
            {"error_type": k, "count": v, "last_seen": error_last_seen[k]}
            for k, v in error_counts.items()
        ]
        errors.sort(key=lambda x: x["count"], reverse=True)
        return errors[:limit]

    def get_recent_errors(self, limit: int = 20) -> list[dict]:
        """获取最近错误"""
        error_events = [e for e in self._events if e.error_type]
        error_events.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.model_dump() for e in error_events[:limit]]

    async def cleanup_old_data(self, days: int = 7):
        """清理过期数据"""
        async with self._lock:
            cutoff = datetime.utcnow() - timedelta(days=days)
            self._events = [e for e in self._events if e.timestamp >= cutoff]
            self._rollups = [r for r in self._rollups if r.window_start >= cutoff]
