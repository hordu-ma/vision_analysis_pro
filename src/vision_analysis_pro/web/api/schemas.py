"""API 响应模型

契约定义（Day 1 决策）：
- bbox 坐标系：像素坐标，格式为 [x1, y1, x2, y2]（左上角与右下角）
- label：字符串类型，对应类目名称（如 "crack", "rust" 等）
- score/confidence：浮点数 [0.0, 1.0]，表示置信度
- 错误响应：统一结构 {code, message, detail?}
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """健康检查响应"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "model_loaded": True,
                "engine": "YOLOInferenceEngine",
                "check": "ready",
                "request_id": "req-1234567890abcdef",
            }
        }
    )

    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="API 版本")
    model_loaded: bool = Field(..., description="模型是否已加载")
    engine: str | None = Field(
        None,
        description="当前推理引擎类型（仅用于展示与排障）",
    )
    check: str | None = Field(
        None,
        description="健康检查类型（如 live / ready）",
    )
    request_id: str | None = Field(
        None,
        description="请求 ID，用于日志关联与排障",
    )


class MetricsResponse(BaseModel):
    """最小指标响应"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "request_count": 128,
                "inference_requests": 32,
                "inference_failures": 1,
                "ready_checks": 12,
                "live_checks": 20,
            }
        }
    )

    status: str = Field(..., description="指标状态")
    request_count: int = Field(..., ge=0, description="累计请求数")
    inference_requests: int = Field(..., ge=0, description="累计推理请求数")
    inference_failures: int = Field(..., ge=0, description="累计推理失败数")
    ready_checks: int = Field(..., ge=0, description="累计就绪检查次数")
    live_checks: int = Field(..., ge=0, description="累计存活检查次数")


class DetectionBox(BaseModel):
    """检测框信息

    坐标系：像素坐标（图片左上角为原点）
    bbox 格式：[x1, y1, x2, y2]（左上角与右下角坐标）
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "label": "crack",
                "confidence": 0.95,
                "bbox": [100.0, 150.0, 300.0, 400.0],
            }
        }
    )

    label: str = Field(..., description="检测类别")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 [0.0, 1.0]")
    bbox: list[float] = Field(
        ...,
        description="边界框坐标 [x1, y1, x2, y2]，像素坐标",
    )


class InferenceResponse(BaseModel):
    """推理响应"""

    model_config = ConfigDict(
        json_schema_extra={
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
                    "engine": "YOLOInferenceEngine",
                    "request_id": "req-1234567890abcdef",
                },
                "visualization": None,
            }
        }
    )

    filename: str = Field(..., description="上传的文件名")
    detections: list[DetectionBox] = Field(..., description="检测结果列表")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="元信息（如推理耗时、模型版本、请求 ID 等）",
    )
    visualization: str | None = Field(
        None,
        description="可视化图像的 base64 编码（当 visualize=true 时返回）",
    )


class ReportInferenceResult(BaseModel):
    """边缘 Agent 单帧推理结果上报结构"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "frame_id": 1,
                "timestamp": 1700000000.0,
                "source_id": "edge-agent-001",
                "detections": [
                    {
                        "label": "crack",
                        "confidence": 0.95,
                        "bbox": [100.0, 150.0, 300.0, 400.0],
                    }
                ],
                "inference_time_ms": 12.4,
                "metadata": {"image_name": "tower_001.jpg"},
            }
        }
    )

    frame_id: int = Field(..., ge=0, description="帧序号")
    timestamp: float = Field(..., description="采集时间戳")
    source_id: str = Field(..., min_length=1, description="数据源标识")
    detections: list[DetectionBox] = Field(
        default_factory=list,
        description="该帧检测结果",
    )
    inference_time_ms: float = Field(0.0, ge=0.0, description="推理耗时（毫秒）")
    metadata: dict[str, Any] = Field(default_factory=dict, description="帧元信息")


class ReportPayloadRequest(BaseModel):
    """边缘 Agent 批量上报请求"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "edge-agent-001",
                "batch_id": "edge-agent-001-1700000000000",
                "report_time": 1700000000.0,
                "results": [
                    {
                        "frame_id": 1,
                        "timestamp": 1700000000.0,
                        "source_id": "edge-agent-001",
                        "detections": [
                            {
                                "label": "crack",
                                "confidence": 0.95,
                                "bbox": [100.0, 150.0, 300.0, 400.0],
                            }
                        ],
                        "inference_time_ms": 12.4,
                        "metadata": {"image_name": "tower_001.jpg"},
                    }
                ],
            }
        }
    )

    device_id: str = Field(..., min_length=1, description="边缘设备标识")
    batch_id: str = Field(..., min_length=1, description="批次 ID")
    report_time: float = Field(..., description="上报时间戳")
    results: list[ReportInferenceResult] = Field(
        default_factory=list,
        description="批次内推理结果列表",
    )


class ReportResponse(BaseModel):
    """边缘 Agent 上报响应"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "accepted",
                "message": "上报已接收",
                "batch_id": "edge-agent-001-1700000000000",
                "result_count": 1,
                "total_detections": 1,
                "request_id": "req-1234567890abcdef",
            }
        }
    )

    status: str = Field(..., description="上报处理状态")
    message: str = Field(..., description="响应消息")
    batch_id: str = Field(..., description="批次 ID")
    result_count: int = Field(..., ge=0, description="接收的结果数量")
    total_detections: int = Field(..., ge=0, description="接收的检测结果总数")
    request_id: str | None = Field(None, description="请求 ID")


class ReportRecordResponse(BaseModel):
    """边缘 Agent 上报批次查询响应"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "found",
                "batch_id": "edge-agent-001-1700000000000",
                "device_id": "edge-agent-001",
                "report_time": 1700000000.0,
                "result_count": 1,
                "total_detections": 1,
                "created_at": 1700000001.0,
                "payload": {
                    "device_id": "edge-agent-001",
                    "batch_id": "edge-agent-001-1700000000000",
                    "report_time": 1700000000.0,
                    "results": [],
                },
                "request_id": "req-1234567890abcdef",
            }
        }
    )

    status: str = Field(..., description="查询状态")
    batch_id: str = Field(..., description="批次 ID")
    device_id: str = Field(..., description="边缘设备标识")
    report_time: float = Field(..., description="上报时间戳")
    result_count: int = Field(..., ge=0, description="接收的结果数量")
    total_detections: int = Field(..., ge=0, description="接收的检测结果总数")
    created_at: float = Field(..., description="服务端接收时间戳")
    payload: dict[str, Any] = Field(..., description="原始上报载荷")
    request_id: str | None = Field(None, description="请求 ID")


class ErrorResponse(BaseModel):
    """统一错误响应结构"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "MODEL_NOT_LOADED",
                "message": "模型未加载",
                "detail": "模型文件不存在: models/best.pt",
                "request_id": "req-1234567890abcdef",
            }
        }
    )

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    detail: str | None = Field(
        None,
        description="详细错误信息（可选）",
    )
    request_id: str | None = Field(
        None,
        description="请求 ID，用于日志关联与排障",
    )
