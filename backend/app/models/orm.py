from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.db.database import Base
from datetime import datetime


class RequestEventORM(Base):
    __tablename__ = "request_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(100), index=True, nullable=False)
    model = Column(String(100), index=True, nullable=False)
    app_id = Column(String(100), index=True, nullable=True)
    latency_ms = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)
    error_type = Column(String(200), nullable=True)
    token_in = Column(Integer, default=0)
    token_out = Column(Integer, default=0)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)


class MetricRollupORM(Base):
    __tablename__ = "metric_rollups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    window_start = Column(DateTime, index=True, nullable=False)
    model = Column(String(100), index=True, nullable=False)
    app_id = Column(String(100), index=True, nullable=True)
    qps = Column(Float, nullable=False)
    success_rate = Column(Float, nullable=False)
    p95_latency = Column(Float, nullable=False)
    error_rate = Column(Float, nullable=False)
