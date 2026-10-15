import time
import uuid
import json
import logging
from typing import Optional
from fastapi import Request, Response, APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
from app.config import settings
from app.models.schemas import RequestEvent
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proxy/v1")
event_bus: Optional[EventBus] = None

# 需要从上游响应头中排除的头（避免传递不兼容的头）
EXCLUDE_RESPONSE_HEADERS = {
    "transfer-encoding", "content-encoding", "content-length",
    "connection", "keep-alive", "server",
}


def init_proxy_router(bus: EventBus):
    """初始化代理路由"""
    global event_bus
    event_bus = bus
    return router


async def _forward_request(path: str, request: Request) -> Response:
    """转发请求到上游服务"""
    if event_bus is None:
        return JSONResponse(status_code=500, content={"error": "服务未初始化"})

    request_id = str(uuid.uuid4())
    model = "未知"
    app_id = request.headers.get("X-App-ID")
    start_time = time.time()
    status = "success"
    error_type = None
    token_in = 0
    token_out = 0

    try:
        body = await request.body()
        body_str = body.decode("utf-8") if body else ""

        if body_str:
            try:
                body_json = json.loads(body_str)
                model = body_json.get("model", "未知")
                token_in = body_json.get("max_tokens", 0)
            except json.JSONDecodeError:
                pass

        upstream_url = f"{settings.UPSTREAM_BASE_URL}{path}"
        logger.info(f"[代理] {request.method} {upstream_url} model={model}")

        # 构建干净的请求头
        headers = {"Content-Type": "application/json"}

        # 获取 API Key
        auth_header = request.headers.get("Authorization", "")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]  # 去掉 "Bearer " 前缀
        elif settings.UPSTREAM_API_KEY:
            api_key = settings.UPSTREAM_API_KEY
        else:
            return JSONResponse(
                status_code=401,
                content={"error": {"type": "未授权", "message": "请先配置 API Key"}},
            )

        headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                content=body,
            )

            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"[代理] 响应 {resp.status_code} 耗时 {latency_ms:.0f}ms")

            # 尝试解析 JSON
            resp_json = None
            try:
                resp_json = resp.json()
            except Exception:
                pass

            # 如果上游返回非 JSON（如 HTML 错误页），封装为统一错误格式
            if resp_json is None:
                status = "error"
                error_type = f"http_{resp.status_code}"
                event = RequestEvent(
                    request_id=request_id, model=model, app_id=app_id,
                    latency_ms=latency_ms, status=status, error_type=error_type,
                    token_in=token_in, token_out=token_out,
                )
                await event_bus.push_event(event)
                return JSONResponse(
                    status_code=resp.status_code,
                    content={
                        "error": {
                            "type": "upstream_error",
                            "message": f"上游服务返回非 JSON 响应 (HTTP {resp.status_code})",
                        }
                    },
                )

            # 处理错误响应
            if resp.status_code >= 400:
                status = "error"
                if isinstance(resp_json, dict):
                    error_info = resp_json.get("error", {})
                    if isinstance(error_info, dict):
                        error_type = error_info.get("message") or error_info.get("type", f"http_{resp.status_code}")
                    elif isinstance(error_info, str):
                        error_type = error_info
                    else:
                        error_type = f"http_{resp.status_code}"
                else:
                    error_type = f"http_{resp.status_code}"

            # 提取 usage 信息
            if isinstance(resp_json, dict):
                usage = resp_json.get("usage", {})
                token_in = usage.get("prompt_tokens", token_in)
                token_out = usage.get("completion_tokens", 0)

            # 记录事件
            event = RequestEvent(
                request_id=request_id, model=model, app_id=app_id,
                latency_ms=latency_ms, status=status, error_type=error_type,
                token_in=token_in, token_out=token_out,
            )
            await event_bus.push_event(event)

            # 构建响应头（排除不兼容的头）
            safe_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() not in EXCLUDE_RESPONSE_HEADERS
            }

            return JSONResponse(
                status_code=resp.status_code,
                content=resp_json,
                headers=safe_headers,
            )

    except httpx.TimeoutException:
        latency_ms = (time.time() - start_time) * 1000
        error_type = "超时"
        status = "error"
        event = RequestEvent(
            request_id=request_id, model=model, app_id=app_id,
            latency_ms=latency_ms, status=status, error_type=error_type,
            token_in=token_in, token_out=token_out,
        )
        await event_bus.push_event(event)
        return JSONResponse(
            status_code=504,
            content={"error": {"type": "超时", "message": "上游请求超时"}},
        )

    except httpx.ConnectError as e:
        latency_ms = (time.time() - start_time) * 1000
        error_type = "连接失败"
        status = "error"
        event = RequestEvent(
            request_id=request_id, model=model, app_id=app_id,
            latency_ms=latency_ms, status=status, error_type=error_type,
            token_in=token_in, token_out=token_out,
        )
        await event_bus.push_event(event)
        return JSONResponse(
            status_code=502,
            content={"error": {"type": "连接失败", "message": f"无法连接上游服务: {e}"}},
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        error_type = type(e).__name__
        status = "error"
        logger.error(f"[代理] 异常: {e}", exc_info=True)
        event = RequestEvent(
            request_id=request_id, model=model, app_id=app_id,
            latency_ms=latency_ms, status=status, error_type=error_type,
            token_in=token_in, token_out=token_out,
        )
        await event_bus.push_event(event)
        return JSONResponse(
            status_code=502,
            content={"error": {"type": "代理错误", "message": str(e)}},
        )


@router.post("/chat/completions")
async def proxy_chat_completions(request: Request):
    """代理聊天补全请求"""
    return await _forward_request("/chat/completions", request)


@router.post("/responses")
async def proxy_responses(request: Request):
    """代理响应请求"""
    return await _forward_request("/responses", request)
