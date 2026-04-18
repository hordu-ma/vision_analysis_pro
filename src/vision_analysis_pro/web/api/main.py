"""FastAPI 应用主入口"""

import logging
import os
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from vision_analysis_pro.settings import get_settings
from vision_analysis_pro.web.api import schemas
from vision_analysis_pro.web.api.routers import inference

logger = logging.getLogger(__name__)

app = FastAPI(
    title="工程基础设施图像识别智能运维系统",
    description="基于 YOLO 的无人机巡检系统后端 API",
    version="0.1.0",
    responses={
        400: {"model": schemas.ErrorResponse, "description": "请求参数错误"},
        503: {
            "model": schemas.ErrorResponse,
            "description": "服务不可用（如模型未加载）",
        },
    },
)

app.state.metrics = {
    "requests_total": 0,
    "requests_in_flight": 0,
    "requests_failed_total": 0,
    "inference_requests_total": 0,
    "inference_failures_total": 0,
    "inference_success_total": 0,
    "health_live_checks_total": 0,
    "health_ready_checks_total": 0,
}

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """为每个请求注入 request_id 并记录最小请求指标。"""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id

    metrics: dict[str, int] = app.state.metrics
    metrics["requests_total"] += 1
    metrics["requests_in_flight"] += 1

    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        metrics["requests_failed_total"] += 1
        logger.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        raise
    finally:
        metrics["requests_in_flight"] -= 1

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(duration_ms)

    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


# 路由注册
app.include_router(inference.router)


def _get_health_payload() -> dict[str, Any]:
    """构造健康检查载荷。"""
    settings = get_settings()

    engine_type = os.getenv("INFERENCE_ENGINE", "yolo").lower()
    if engine_type == "stub":
        engine_name = "StubInferenceEngine"
        model_loaded = False
    elif engine_type == "onnx":
        engine_name = "ONNXInferenceEngine"
        model_path = os.getenv("ONNX_MODEL_PATH", "models/best.onnx")
        model_loaded = Path(model_path).exists()
    else:
        engine_name = "YOLOInferenceEngine"
        model_path = os.getenv("YOLO_MODEL_PATH", "runs/train/exp/weights/best.pt")
        model_loaded = Path(model_path).exists() or settings.model_path.exists()

    return {
        "status": "healthy",
        "version": app.version,
        "model_loaded": model_loaded,
        "engine": engine_name,
    }


# 统一异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTPException，返回统一的 ErrorResponse 格式"""
    request_id = getattr(request.state, "request_id", None)

    if isinstance(exc.detail, dict):
        content = dict(exc.detail)
        if request_id and "request_id" not in content:
            content["request_id"] = request_id
        return JSONResponse(status_code=exc.status_code, content=content)

    error_code = f"HTTP_{exc.status_code}"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": error_code,
            "message": str(exc.detail) if exc.detail else "请求错误",
            "detail": None,
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """捕获所有未处理的异常，返回统一的 500 错误"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
            "detail": str(exc),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.get("/", response_model=schemas.HealthResponse)
async def root() -> JSONResponse:
    """健康检查"""
    return await health()


@app.get("/api/v1/health", response_model=schemas.HealthResponse)
async def health() -> JSONResponse:
    """兼容旧路径的健康检查接口。"""
    return JSONResponse(content=_get_health_payload())


@app.get("/api/v1/health/live", response_model=schemas.HealthResponse)
async def health_live(request: Request) -> JSONResponse:
    """存活检查接口。"""
    metrics: dict[str, int] = app.state.metrics
    metrics["health_live_checks_total"] += 1

    payload = _get_health_payload()
    payload["status"] = "alive"
    payload["check"] = "live"
    payload["model_loaded"] = True
    payload["request_id"] = getattr(request.state, "request_id", None)
    return JSONResponse(content=payload)


@app.get("/api/v1/health/ready", response_model=schemas.HealthResponse)
async def health_ready(request: Request) -> JSONResponse:
    """就绪检查接口。"""
    metrics: dict[str, int] = app.state.metrics
    metrics["health_ready_checks_total"] += 1

    payload = _get_health_payload()
    payload["check"] = "ready"
    payload["request_id"] = getattr(request.state, "request_id", None)

    if not payload["model_loaded"]:
        payload["status"] = "degraded"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
        )

    payload["status"] = "ready"
    return JSONResponse(content=payload)


@app.get("/api/v1/metrics")
async def metrics() -> PlainTextResponse:
    """最小 Prometheus 风格指标端点。"""
    metrics_data: dict[str, int] = app.state.metrics
    lines = [
        "# HELP vision_api_requests_total Total HTTP requests.",
        "# TYPE vision_api_requests_total counter",
        f"vision_api_requests_total {metrics_data['requests_total']}",
        "# HELP vision_api_requests_in_flight In-flight HTTP requests.",
        "# TYPE vision_api_requests_in_flight gauge",
        f"vision_api_requests_in_flight {metrics_data['requests_in_flight']}",
        "# HELP vision_api_requests_failed_total Total failed HTTP requests.",
        "# TYPE vision_api_requests_failed_total counter",
        f"vision_api_requests_failed_total {metrics_data['requests_failed_total']}",
        "# HELP vision_api_inference_requests_total Total inference requests.",
        "# TYPE vision_api_inference_requests_total counter",
        f"vision_api_inference_requests_total {metrics_data['inference_requests_total']}",
        "# HELP vision_api_inference_failures_total Total failed inference requests.",
        "# TYPE vision_api_inference_failures_total counter",
        f"vision_api_inference_failures_total {metrics_data['inference_failures_total']}",
        "# HELP vision_api_health_live_checks_total Total live health checks.",
        "# TYPE vision_api_health_live_checks_total counter",
        f"vision_api_health_live_checks_total {metrics_data['health_live_checks_total']}",
        "# HELP vision_api_health_ready_checks_total Total ready health checks.",
        "# TYPE vision_api_health_ready_checks_total counter",
        f"vision_api_health_ready_checks_total {metrics_data['health_ready_checks_total']}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n")
