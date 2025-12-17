"""推理相关 API"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

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


@router.post("/image", response_model=schemas.InferenceResponse)
async def inference_image(
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Any, Depends(get_inference_engine)],
    file: UploadFile = File(...),
) -> schemas.InferenceResponse:
    """图像推理接口"""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="上传的文件为空"
        )

    # 调用推理引擎
    raw_result = engine.predict(
        file_bytes, conf=settings.confidence_threshold, iou=settings.iou_threshold
    )  # type: ignore[arg-type]
    detections = _serialize_detections(raw_result)

    return schemas.InferenceResponse(
        filename=file.filename,
        detections=detections,
        metadata={"engine": engine.__class__.__name__},
    )
