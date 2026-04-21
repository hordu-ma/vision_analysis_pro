"""FastAPI 应用主入口"""

import argparse
import logging
import os
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vision_analysis_pro.logging_utils import configure_logging
from vision_analysis_pro.settings import get_settings
from vision_analysis_pro.web.api import schemas
from vision_analysis_pro.web.api.metrics import ApiMetrics, create_api_metrics
from vision_analysis_pro.web.api.routers import inference, reports

configure_logging("vision_api", log_format=get_settings().log_format)

logger = logging.getLogger(__name__)


def _parse_cors_allow_origins(raw_origins: str) -> list[str]:
    """解析逗号分隔的 CORS 白名单。"""
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["*"]


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

app.state.metrics = create_api_metrics()


def _matched_route_path(request: Request) -> str:
    """返回已匹配的路由模板，避免原始参数路径造成高基数。"""
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_allow_origins(get_settings().cors_allow_origins),
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
    trace_id = request.headers.get("x-trace-id")
    request.state.request_id = request_id
    request.state.trace_id = trace_id

    metrics: ApiMetrics = app.state.metrics
    metrics.inc("requests_total")
    metrics.inc_gauge("requests_in_flight")
    route_path = _matched_route_path(request)

    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        metrics.inc("requests_failed_total")
        logger.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "method": request.method,
                "path": route_path,
            },
        )
        raise
    finally:
        metrics.dec_gauge("requests_in_flight")

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    metrics.observe("request_duration_ms", duration_ms)
    metrics.inc_request_status(
        method=request.method,
        path=route_path,
        status_code=response.status_code,
    )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    if trace_id:
        response.headers["X-Trace-ID"] = trace_id

    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "method": request.method,
            "path": route_path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


# 路由注册
app.include_router(inference.router)
app.include_router(reports.router)


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
    elif engine_type == "yolo":
        engine_name = "YOLOInferenceEngine"
        model_path = os.getenv("YOLO_MODEL_PATH", "runs/train/exp/weights/best.pt")
        model_loaded = Path(model_path).exists() or settings.model_path.exists()
    else:
        engine_name = "UnknownInferenceEngine"
        model_loaded = False

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
    metrics: ApiMetrics = app.state.metrics
    metrics.inc("health_live_checks_total")

    payload = _get_health_payload()
    payload["status"] = "alive"
    payload["check"] = "live"
    payload["model_loaded"] = True
    payload["request_id"] = getattr(request.state, "request_id", None)
    return JSONResponse(content=payload)


@app.get("/api/v1/health/ready", response_model=schemas.HealthResponse)
async def health_ready(request: Request) -> JSONResponse:
    """就绪检查接口。"""
    metrics: ApiMetrics = app.state.metrics
    metrics.inc("health_ready_checks_total")

    payload = _get_health_payload()
    payload["check"] = "ready"
    payload["request_id"] = getattr(request.state, "request_id", None)

    if not payload["model_loaded"]:
        payload["status"] = "degraded"
        metrics.inc("health_ready_failures_total")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
        )

    payload["status"] = "ready"
    return JSONResponse(content=payload)


@app.get("/api/v1/metrics")
async def metrics() -> Response:
    """Prometheus 指标端点。"""
    metrics_data: ApiMetrics = app.state.metrics
    return Response(
        content=metrics_data.render(),
        headers={"Content-Type": metrics_data.content_type},
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    """构造 API 服务命令行参数解析器。"""
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="启动 Vision Analysis Pro API 服务",
    )
    parser.add_argument(
        "--host",
        default=settings.api_host,
        help=f"API 监听地址，默认 {settings.api_host}",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.api_port,
        help=f"API 监听端口，默认 {settings.api_port}",
    )
    parser.add_argument(
        "--reload",
        action=argparse.BooleanOptionalAction,
        default=settings.api_reload,
        help=f"是否启用自动重载，默认 {settings.api_reload}",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn 日志级别，默认 info",
    )
    return parser


def main() -> None:
    """控制台脚本入口。"""
    import uvicorn

    args = _build_arg_parser().parse_args()
    configure_logging(
        "vision_api",
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        log_format=get_settings().log_format,
    )
    uvicorn.run(
        "vision_analysis_pro.web.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        log_config=None,
    )
