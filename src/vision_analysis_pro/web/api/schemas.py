"""API 响应模型

契约定义（Day 1 决策）：
- bbox 坐标系：像素坐标，格式为 [x1, y1, x2, y2]（左上角与右下角）
- label：字符串类型，对应类目名称（如 "crack", "rust" 等）
- score/confidence：浮点数 [0.0, 1.0]，表示置信度
- 错误响应：统一结构 {code, message, detail?}
"""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="服务状态", example="healthy")
    version: str = Field(..., description="API 版本", example="0.1.0")
    model_loaded: bool = Field(..., description="模型是否已加载", example=True)


class DetectionBox(BaseModel):
    """检测框信息

    坐标系：像素坐标（图片左上角为原点）
    bbox 格式：[x1, y1, x2, y2]（左上角与右下角坐标）
    """

    label: str = Field(..., description="检测类别", example="crack")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="置信度 [0.0, 1.0]", example=0.95
    )
    bbox: list[float] = Field(
        ...,
        description="边界框坐标 [x1, y1, x2, y2]，像素坐标",
        example=[100.0, 150.0, 300.0, 400.0],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "label": "crack",
                "confidence": 0.95,
                "bbox": [100.0, 150.0, 300.0, 400.0],
            }
        }


class InferenceResponse(BaseModel):
    """推理响应"""

    filename: str = Field(..., description="上传的文件名", example="test_image.jpg")
    detections: list[DetectionBox] = Field(..., description="检测结果列表")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="元信息（如推理耗时、模型版本等）",
        example={"inference_time_ms": 45.2, "model_version": "v1.0"},
    )

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "test_image.jpg",
                "detections": [
                    {
                        "label": "crack",
                        "confidence": 0.95,
                        "bbox": [100.0, 150.0, 300.0, 400.0],
                    },
                    {
                        "label": "rust",
                        "confidence": 0.88,
                        "bbox": [450.0, 200.0, 550.0, 350.0],
                    },
                ],
                "metadata": {
                    "inference_time_ms": 45.2,
                    "model_version": "v1.0",
                },
            }
        }


class ErrorResponse(BaseModel):
    """统一错误响应结构"""

    code: str = Field(..., description="错误码", example="MODEL_NOT_LOADED")
    message: str = Field(..., description="错误消息", example="模型未加载")
    detail: str | None = Field(
        None,
        description="详细错误信息（可选）",
        example="模型文件不存在: models/best.pt",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "code": "MODEL_NOT_LOADED",
                "message": "模型未加载",
                "detail": "模型文件不存在: models/best.pt",
            }
        }
