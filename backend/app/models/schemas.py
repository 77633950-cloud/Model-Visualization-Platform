from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RequestEvent(BaseModel):
    """请求事件模型"""
    request_id: str
    model: str
    app_id: Optional[str] = None
    latency_ms: float
    status: str
    error_type: Optional[str] = None
    token_in: int = 0
    token_out: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MetricRollup(BaseModel):
    """指标聚合模型"""
    window_start: datetime
    model: str
    app_id: Optional[str] = None
    qps: float
    success_rate: float
    p95_latency: float
    error_rate: float


class ModelHealth(BaseModel):
    """模型健康状态模型"""
    model: str
    is_available: bool
    last_ok_at: Optional[datetime] = None
    degraded_reason: Optional[str] = None


class OverviewMetrics(BaseModel):
    """概览指标模型"""
    qps: float
    success_rate: float
    p50_latency: float
    p95_latency: float
    error_rate: float
    model_health: list[ModelHealth]


class TimeSeriesPoint(BaseModel):
    """时间序列数据点模型"""
    timestamp: datetime
    qps: float
    success_rate: float
    p95_latency: float
    error_rate: float


class ErrorItem(BaseModel):
    """错误项模型"""
    error_type: str
    count: int
    last_seen: datetime


class ProxyResponse(BaseModel):
    """代理响应模型"""
    status_code: int
    headers: dict
    body: dict
