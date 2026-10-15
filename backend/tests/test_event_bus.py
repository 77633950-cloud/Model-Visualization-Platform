import pytest
import asyncio
from datetime import datetime
from app.services.event_bus import EventBus
from app.models.schemas import RequestEvent, MetricRollup


@pytest.fixture
def event_bus():
    return EventBus(window_seconds=5)


@pytest.fixture
def sample_event():
    return RequestEvent(
        request_id="test-001",
        model="gpt-4",
        app_id="test-app",
        latency_ms=150.0,
        status="success",
        token_in=100,
        token_out=50,
        timestamp=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_push_event(event_bus, sample_event):
    await event_bus.push_event(sample_event)
    assert len(event_bus._events) == 1
    assert event_bus._events[0].request_id == "test-001"


@pytest.mark.asyncio
async def test_aggregation_worker(event_bus):
    events = [
        RequestEvent(
            request_id=f"test-{i}",
            model="gpt-4",
            latency_ms=100.0 + i * 10,
            status="success" if i < 9 else "error",
            error_type="rate_limit" if i == 9 else None,
            timestamp=datetime.utcnow(),
        )
        for i in range(10)
    ]

    for e in events:
        await event_bus.push_event(e)

    await event_bus._compute_rollups()

    assert len(event_bus._rollups) > 0
    rollup = event_bus._rollups[-1]
    assert rollup.model == "gpt-4"
    assert rollup.success_rate == 0.9


def test_get_overview_empty(event_bus):
    overview = event_bus.get_overview(minutes=5)
    assert overview["qps"] == 0.0
    assert overview["success_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_overview_with_data(event_bus):
    events = [
        RequestEvent(
            request_id=f"test-{i}",
            model="gpt-4",
            latency_ms=100.0 + i,
            status="success" if i < 8 else "error",
            error_type="timeout" if i >= 8 else None,
            timestamp=datetime.utcnow(),
        )
        for i in range(10)
    ]

    for e in events:
        await event_bus.push_event(e)

    overview = event_bus.get_overview(minutes=5)
    assert overview["qps"] > 0
    assert overview["success_rate"] == 0.8
    assert overview["error_rate"] == 0.2
    assert overview["p50_latency"] > 0
    assert overview["p95_latency"] > 0


def test_get_top_errors(event_bus):
    event_bus._events = [
        RequestEvent(
            request_id=f"err-{i}",
            model="gpt-4",
            latency_ms=200.0,
            status="error",
            error_type="rate_limit" if i < 5 else "timeout",
            timestamp=datetime.utcnow(),
        )
        for i in range(8)
    ]

    errors = event_bus.get_top_errors(limit=5)
    assert len(errors) <= 5
    if len(errors) > 0:
        assert errors[0]["error_type"] == "rate_limit"
        assert errors[0]["count"] == 5


def test_get_timeseries(event_bus):
    now = datetime.utcnow()
    event_bus._rollups = [
        MetricRollup(
            window_start=now,
            model="gpt-4",
            qps=10.0,
            success_rate=0.95,
            p95_latency=200.0,
            error_rate=0.05,
        )
    ]

    ts = event_bus.get_timeseries(minutes=60)
    assert len(ts) == 1
    assert ts[0]["model"] == "gpt-4"


def test_model_health_update(event_bus):
    success_event = RequestEvent(
        request_id="h-001",
        model="gpt-4",
        latency_ms=100.0,
        status="success",
        timestamp=datetime.utcnow(),
    )
    event_bus._update_model_health(success_event)
    assert event_bus._model_health["gpt-4"].is_available == True


def test_model_health_degradation(event_bus):
    error_event = RequestEvent(
        request_id="h-002",
        model="gpt-4",
        latency_ms=5000.0,
        status="error",
        error_type="超时",
        timestamp=datetime.utcnow(),
    )
    event_bus._update_model_health(error_event)
    assert event_bus._model_health["gpt-4"].is_available == False
    assert event_bus._model_health["gpt-4"].degraded_reason == "超时"
