"""推理相关 API"""

import base64
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from vision_analysis_pro.core.preprocessing.visualization import draw_detections
from vision_analysis_pro.settings import Settings, get_settings
from vision_analysis_pro.web.api import schemas
from vision_analysis_pro.web.api.deps import get_inference_engine

router = APIRouter(prefix="/api/v1/inference", tags=["inference"])


def _serialize_detections(result: Any) -> list[schemas.DetectionBox]:
    """将推理结果转换为标准结构

    契约：bbox 格式为 [x1, y1, x2, y2]，像素坐标
    为兼容未来接入 YOLO 原生结果，预留兜底分支。
    """
    detections: list[schemas.DetectionBox] = []

    if isinstance(result, list) and result and isinstance(result[0], dict):
        for item in result:
            # 统一 bbox 格式（支持 box/bbox 两种 key）
            bbox_data = item.get("bbox") or item.get("box")
            if bbox_data:
                # 确保 bbox 是列表格式
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

    # 兜底：直接返回空列表，等待后续集成 YOLO 结构化输出
    return detections


# 文件校验常量
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}


@router.post(
    "/image",
    response_model=schemas.InferenceResponse,
    responses={
        400: {"model": schemas.ErrorResponse},
        500: {"model": schemas.ErrorResponse},
    },
)
async def inference_image(
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Any, Depends(get_inference_engine)],
    file: UploadFile = File(...),
    visualize: bool = Query(False, description="是否返回可视化图像"),
) -> schemas.InferenceResponse:
    """图像推理接口"""
    # 文件校验：空文件
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

    # 文件校验：大小限制
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": "文件大小超过限制",
                "detail": f"文件大小: {len(file_bytes)} bytes, 最大允许: {MAX_FILE_SIZE} bytes",
            },
        )

    # 文件校验：MIME 类型
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FORMAT",
                "message": "不支持的文件格式",
                "detail": f"当前格式: {file.content_type}, 支持格式: {', '.join(ALLOWED_MIME_TYPES)}",
            },
        )

    # 调用推理引擎
    try:
        raw_result = engine.predict(
            file_bytes, conf=settings.confidence_threshold, iou=settings.iou_threshold
        )  # type: ignore[arg-type]
        detections = _serialize_detections(raw_result)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INFERENCE_ERROR",
                "message": "推理失败",
                "detail": str(e),
            },
        ) from e

    # 生成可视化图像（可选）
    visualization_data = None
    if visualize and detections:
        try:
            # 转换 DetectionBox 为字典格式
            detection_dicts = [
                {
                    "label": det.label,
                    "confidence": det.confidence,
                    "bbox": det.bbox,
                }
                for det in detections
            ]
            vis_bytes = draw_detections(file_bytes, detection_dicts)
            # 转换为 base64 Data URI
            vis_base64 = base64.b64encode(vis_bytes).decode("utf-8")
            visualization_data = f"data:image/jpeg;base64,{vis_base64}"
        except Exception:
            # 可视化失败不影响推理结果返回
            visualization_data = None

    return schemas.InferenceResponse(
        filename=file.filename or "unknown",
        detections=detections,
        metadata={"engine": engine.__class__.__name__},
        visualization=visualization_data,
    )
