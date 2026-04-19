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
from fastapi.responses import JSONResponse, PlainTextResponse

from vision_analysis_pro.logging_utils import configure_logging
from vision_analysis_pro.settings import get_settings
from vision_analysis_pro.web.api import schemas
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

app.state.metrics = {
    "requests_total": 0,
    "requests_in_flight": 0,
    "requests_failed_total": 0,
    "request_duration_ms_sum": 0.0,
    "request_duration_ms_count": 0,
    "request_duration_ms_last": 0.0,
    "inference_requests_total": 0,
    "inference_failures_total": 0,
    "inference_success_total": 0,
    "inference_duration_ms_sum": 0.0,
    "inference_duration_ms_count": 0,
    "inference_duration_ms_last": 0.0,
    "inference_detections_total": 0,
    "inference_visualizations_total": 0,
    "inference_input_bytes_total": 0,
    "report_requests_total": 0,
    "report_query_requests_total": 0,
    "report_results_total": 0,
    "report_detections_total": 0,
    "report_duplicates_total": 0,
    "report_not_found_total": 0,
    "health_live_checks_total": 0,
    "health_ready_checks_total": 0,
    "health_ready_failures_total": 0,
    "request_status_total": {},
}


def _matched_route_path(request: Request) -> str:
    """返回已匹配的路由模板，避免原始参数路径造成高基数。"""
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


def _record_request_status_metric(
    metrics: dict[str, Any],
    *,
    method: str,
    path: str,
    status_code: int,
) -> None:
    key = (method, path, str(status_code))
    request_status_total: dict[tuple[str, str, str], int] = metrics[
        "request_status_total"
    ]
    request_status_total[key] = request_status_total.get(key, 0) + 1


def _render_metric_lines(
    name: str, help_text: str, metric_type: str, value: Any
) -> list[str]:
    return [
        f"# HELP {name} {help_text}",
        f"# TYPE {name} {metric_type}",
        f"{name} {value}",
    ]


def _prometheus_labels(**labels: str) -> str:
    escaped = []
    for key, value in labels.items():
        safe_value = value.replace("\\", "\\\\").replace('"', '\\"')
        escaped.append(f'{key}="{safe_value}"')
    return "{" + ",".join(escaped) + "}"


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
    request.state.request_id = request_id

    metrics: dict[str, Any] = app.state.metrics
    metrics["requests_total"] += 1
    metrics["requests_in_flight"] += 1
    route_path = _matched_route_path(request)

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
                "path": route_path,
            },
        )
        raise
    finally:
        metrics["requests_in_flight"] -= 1

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    metrics["request_duration_ms_sum"] += duration_ms
    metrics["request_duration_ms_count"] += 1
    metrics["request_duration_ms_last"] = duration_ms
    _record_request_status_metric(
        metrics,
        method=request.method,
        path=route_path,
        status_code=response.status_code,
    )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(duration_ms)

    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
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
    metrics: dict[str, Any] = app.state.metrics
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
    metrics: dict[str, Any] = app.state.metrics
    metrics["health_ready_checks_total"] += 1

    payload = _get_health_payload()
    payload["check"] = "ready"
    payload["request_id"] = getattr(request.state, "request_id", None)

    if not payload["model_loaded"]:
        payload["status"] = "degraded"
        metrics["health_ready_failures_total"] += 1
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
        )

    payload["status"] = "ready"
    return JSONResponse(content=payload)


@app.get("/api/v1/metrics")
async def metrics() -> PlainTextResponse:
    """最小 Prometheus 风格指标端点。"""
    metrics_data: dict[str, Any] = app.state.metrics
    lines: list[str] = []
    for name, help_text, metric_type, value in [
        (
            "vision_api_requests_total",
            "Total HTTP requests.",
            "counter",
            metrics_data["requests_total"],
        ),
        (
            "vision_api_requests_in_flight",
            "In-flight HTTP requests.",
            "gauge",
            metrics_data["requests_in_flight"],
        ),
        (
            "vision_api_requests_failed_total",
            "Total failed HTTP requests.",
            "counter",
            metrics_data["requests_failed_total"],
        ),
        (
            "vision_api_request_duration_ms_sum",
            "Total HTTP request duration in milliseconds.",
            "counter",
            metrics_data["request_duration_ms_sum"],
        ),
        (
            "vision_api_request_duration_ms_count",
            "Count of observed HTTP request durations.",
            "counter",
            metrics_data["request_duration_ms_count"],
        ),
        (
            "vision_api_request_duration_ms_last",
            "Last observed HTTP request duration in milliseconds.",
            "gauge",
            metrics_data["request_duration_ms_last"],
        ),
        (
            "vision_api_inference_requests_total",
            "Total inference requests.",
            "counter",
            metrics_data["inference_requests_total"],
        ),
        (
            "vision_api_inference_failures_total",
            "Total failed inference requests.",
            "counter",
            metrics_data["inference_failures_total"],
        ),
        (
            "vision_api_inference_success_total",
            "Total successful inference requests.",
            "counter",
            metrics_data["inference_success_total"],
        ),
        (
            "vision_api_inference_duration_ms_sum",
            "Total inference duration in milliseconds.",
            "counter",
            metrics_data["inference_duration_ms_sum"],
        ),
        (
            "vision_api_inference_duration_ms_count",
            "Count of observed inference durations.",
            "counter",
            metrics_data["inference_duration_ms_count"],
        ),
        (
            "vision_api_inference_duration_ms_last",
            "Last observed inference duration in milliseconds.",
            "gauge",
            metrics_data["inference_duration_ms_last"],
        ),
        (
            "vision_api_inference_detections_total",
            "Total detections returned by inference requests.",
            "counter",
            metrics_data["inference_detections_total"],
        ),
        (
            "vision_api_inference_visualizations_total",
            "Total inference requests returning visualizations.",
            "counter",
            metrics_data["inference_visualizations_total"],
        ),
        (
            "vision_api_inference_input_bytes_total",
            "Total input bytes accepted by inference requests.",
            "counter",
            metrics_data["inference_input_bytes_total"],
        ),
        (
            "vision_api_report_requests_total",
            "Total edge report requests.",
            "counter",
            metrics_data["report_requests_total"],
        ),
        (
            "vision_api_report_query_requests_total",
            "Total edge report query requests.",
            "counter",
            metrics_data["report_query_requests_total"],
        ),
        (
            "vision_api_report_results_total",
            "Total edge inference results received.",
            "counter",
            metrics_data["report_results_total"],
        ),
        (
            "vision_api_report_detections_total",
            "Total edge detections received.",
            "counter",
            metrics_data["report_detections_total"],
        ),
        (
            "vision_api_report_duplicates_total",
            "Total duplicate report batches ignored.",
            "counter",
            metrics_data["report_duplicates_total"],
        ),
        (
            "vision_api_report_not_found_total",
            "Total report queries that missed persisted batches.",
            "counter",
            metrics_data["report_not_found_total"],
        ),
        (
            "vision_api_health_live_checks_total",
            "Total live health checks.",
            "counter",
            metrics_data["health_live_checks_total"],
        ),
        (
            "vision_api_health_ready_checks_total",
            "Total ready health checks.",
            "counter",
            metrics_data["health_ready_checks_total"],
        ),
        (
            "vision_api_health_ready_failures_total",
            "Total failed ready health checks.",
            "counter",
            metrics_data["health_ready_failures_total"],
        ),
    ]:
        lines.extend(_render_metric_lines(name, help_text, metric_type, value))

    lines.extend(
        [
            "# HELP vision_api_request_status_total Total HTTP requests by method, route and status code.",
            "# TYPE vision_api_request_status_total counter",
        ]
    )
    request_status_total: dict[tuple[str, str, str], int] = metrics_data[
        "request_status_total"
    ]
    for (method, path, status_code), value in sorted(request_status_total.items()):
        labels = _prometheus_labels(
            method=method,
            path=path,
            status_code=status_code,
        )
        lines.append(f"vision_api_request_status_total{labels} {value}")

    return PlainTextResponse("\n".join(lines) + "\n")


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
