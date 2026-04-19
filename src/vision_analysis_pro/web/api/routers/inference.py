"""推理相关 API"""

import base64
import logging
import time
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)

from vision_analysis_pro.core.preprocessing.visualization import draw_detections
from vision_analysis_pro.settings import Settings, get_settings
from vision_analysis_pro.web.api import schemas
from vision_analysis_pro.web.api.deps import get_inference_engine

router = APIRouter(prefix="/api/v1/inference", tags=["inference"])
logger = logging.getLogger(__name__)

# 文件校验常量
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}


def _record_inference_metrics(
    metrics: dict[str, Any],
    *,
    inference_time_ms: float,
    input_bytes: int,
    detection_count: int = 0,
    visualized: bool = False,
    success: bool,
) -> None:
    metrics["inference_duration_ms_sum"] += inference_time_ms
    metrics["inference_duration_ms_count"] += 1
    metrics["inference_duration_ms_last"] = inference_time_ms
    metrics["inference_input_bytes_total"] += input_bytes
    if success:
        metrics["inference_success_total"] += 1
        metrics["inference_detections_total"] += detection_count
        if visualized:
            metrics["inference_visualizations_total"] += 1


def _serialize_detections(result: Any) -> list[schemas.DetectionBox]:
    """将推理结果转换为标准结构

    契约：bbox 格式为 [x1, y1, x2, y2]，像素坐标
    为兼容未来接入 YOLO 原生结果，预留兜底分支。
    """
    detections: list[schemas.DetectionBox] = []

    if isinstance(result, list) and result and isinstance(result[0], dict):
        for item in result:
            bbox_data = item.get("bbox") or item.get("box")
            if bbox_data:
                bbox_list = (
                    list(bbox_data)
                    if isinstance(bbox_data, (tuple, list))
                    else bbox_data
                )
                detections.append(
                    schemas.DetectionBox(
                        label=str(item["label"]),
                        confidence=float(item["confidence"]),
                        bbox=bbox_list,
                    )
                )
        return detections

    return detections


@router.post(
    "/image",
    response_model=schemas.InferenceResponse,
    responses={
        400: {"model": schemas.ErrorResponse},
        500: {"model": schemas.ErrorResponse},
    },
)
async def inference_image(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Any, Depends(get_inference_engine)],
    file: UploadFile = File(...),
    visualize: bool = Query(False, description="是否返回可视化图像"),
) -> schemas.InferenceResponse:
    """图像推理接口"""
    request_id = getattr(request.state, "request_id", "unknown")
    start_time = time.perf_counter()

    logger.info(
        "inference_request_received",
        extra={
            "request_id": request_id,
            "upload_filename": file.filename,
            "content_type": file.content_type,
            "visualize": visualize,
        },
    )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_FILE",
                "message": "上传的文件为空",
                "detail": f"文件名: {file.filename}",
            },
        )

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": "文件大小超过限制",
                "detail": (
                    f"文件大小: {len(file_bytes)} bytes, "
                    f"最大允许: {MAX_FILE_SIZE} bytes"
                ),
            },
        )

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FORMAT",
                "message": "不支持的文件格式",
                "detail": (
                    f"当前格式: {file.content_type}, "
                    f"支持格式: {', '.join(ALLOWED_MIME_TYPES)}"
                ),
            },
        )

    metrics: dict[str, Any] = request.app.state.metrics
    metrics["inference_requests_total"] += 1
    try:
        raw_result = engine.predict(
            file_bytes,
            conf=settings.confidence_threshold,
            iou=settings.iou_threshold,
        )  # type: ignore[arg-type]
        detections = _serialize_detections(raw_result)
    except RuntimeError as e:
        inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        metrics["inference_failures_total"] += 1
        _record_inference_metrics(
            metrics,
            inference_time_ms=inference_time_ms,
            input_bytes=len(file_bytes),
            success=False,
        )
        logger.exception(
            "inference_request_failed",
            extra={
                "request_id": request_id,
                "upload_filename": file.filename,
                "engine": engine.__class__.__name__,
                "input_bytes": len(file_bytes),
                "inference_time_ms": inference_time_ms,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INFERENCE_ERROR",
                "message": "推理失败",
                "detail": str(e),
            },
        ) from e

    visualization_data = None
    if visualize and detections:
        try:
            detection_dicts = [
                {
                    "label": det.label,
                    "confidence": det.confidence,
                    "bbox": det.bbox,
                }
                for det in detections
            ]
            vis_bytes = draw_detections(file_bytes, detection_dicts)
            vis_base64 = base64.b64encode(vis_bytes).decode("utf-8")
            visualization_data = f"data:image/jpeg;base64,{vis_base64}"
        except Exception:
            visualization_data = None

    inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    detection_count = len(detections)
    visualized = visualization_data is not None
    _record_inference_metrics(
        metrics,
        inference_time_ms=inference_time_ms,
        input_bytes=len(file_bytes),
        detection_count=detection_count,
        visualized=visualized,
        success=True,
    )

    logger.info(
        "inference_request_completed",
        extra={
            "request_id": request_id,
            "upload_filename": file.filename,
            "engine": engine.__class__.__name__,
            "detections": detection_count,
            "input_bytes": len(file_bytes),
            "visualized": visualized,
            "inference_time_ms": inference_time_ms,
        },
    )

    return schemas.InferenceResponse(
        filename=file.filename or "unknown",
        detections=detections,
        metadata={
            "engine": engine.__class__.__name__,
            "request_id": request_id,
            "inference_time_ms": inference_time_ms,
            "detection_count": detection_count,
        },
        visualization=visualization_data,
    )
