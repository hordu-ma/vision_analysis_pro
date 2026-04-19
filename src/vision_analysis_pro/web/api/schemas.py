"""API 响应模型

契约定义（Day 1 决策）：
- bbox 坐标系：像素坐标，格式为 [x1, y1, x2, y2]（左上角与右下角）
- label：字符串类型，对应类目名称（如 "crack", "rust" 等）
- score/confidence：浮点数 [0.0, 1.0]，表示置信度
- 错误响应：统一结构 {code, message, detail?}
"""

from typing import Any, Literal

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


class BatchInferenceResponse(BaseModel):
    """批量推理响应。"""

    files: list[InferenceResponse] = Field(
        default_factory=list,
        description="逐文件推理结果列表",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="批量推理元信息（请求 ID、总耗时、文件数等）",
    )


class InferenceTaskResponse(BaseModel):
    """批量推理异步任务响应。"""

    task_id: str = Field(..., description="任务 ID")
    status: Literal[
        "pending",
        "running",
        "completed",
        "failed",
        "partial_failed",
        "cancelled",
    ] = Field(
        ...,
        description="任务状态",
    )
    created_at: float = Field(..., description="任务创建时间")
    updated_at: float = Field(..., description="任务更新时间")
    file_count: int = Field(..., ge=0, description="任务文件数")
    completed_files: int = Field(..., ge=0, description="已完成文件数")
    progress: int = Field(..., ge=0, le=100, description="任务进度")
    results: list[InferenceResponse] = Field(
        default_factory=list, description="已完成结果"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="任务元信息")
    error: dict[str, str] | None = Field(None, description="失败信息")


class InferenceTaskFileResult(BaseModel):
    """批量任务中的单文件执行结果。"""

    filename: str = Field(..., description="文件名")
    status: Literal["completed", "failed"] = Field(..., description="文件处理状态")
    result: InferenceResponse | None = Field(None, description="成功时的推理结果")
    error: dict[str, str] | None = Field(None, description="失败信息")


class InferenceTaskDetailResponse(InferenceTaskResponse):
    """批量任务详情响应。"""

    files: list[InferenceTaskFileResult] = Field(
        default_factory=list,
        description="文件级执行结果列表",
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


ReviewStatus = Literal["pending", "confirmed", "false_positive", "ignored"]


class ReportFrameReviewResponse(BaseModel):
    """单帧人工复核响应。"""

    frame_id: int = Field(..., ge=0, description="帧序号")
    status: ReviewStatus = Field(..., description="人工复核状态")
    note: str = Field("", description="人工备注")
    reviewer: str = Field("", description="复核人")
    updated_at: float = Field(..., description="复核更新时间戳")


class ReportReviewRequest(BaseModel):
    """人工复核写入请求。"""

    status: ReviewStatus = Field(..., description="人工复核状态")
    note: str = Field("", max_length=500, description="人工备注")
    reviewer: str = Field("", max_length=100, description="复核人")


class ReportReviewResponse(BaseModel):
    """人工复核写入响应。"""

    status: str = Field(..., description="写入状态")
    batch_id: str = Field(..., description="批次 ID")
    review: ReportFrameReviewResponse = Field(..., description="复核结果")
    request_id: str | None = Field(None, description="请求 ID")


class ReportFrameResultResponse(BaseModel):
    """带复核信息的单帧详情。"""

    frame_id: int = Field(..., ge=0, description="帧序号")
    timestamp: float = Field(..., description="采集时间戳")
    source_id: str = Field(..., description="数据源标识")
    detections: list[DetectionBox] = Field(default_factory=list, description="检测结果")
    inference_time_ms: float = Field(..., ge=0.0, description="推理耗时（毫秒）")
    metadata: dict[str, Any] = Field(default_factory=dict, description="帧元信息")
    review: ReportFrameReviewResponse | None = Field(None, description="人工复核信息")


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
    results: list[ReportFrameResultResponse] = Field(
        default_factory=list,
        description="带复核信息的单帧详情",
    )
    payload: dict[str, Any] = Field(..., description="原始上报载荷")
    request_id: str | None = Field(None, description="请求 ID")


class ReportBatchSummaryResponse(BaseModel):
    """边缘上报批次摘要。"""

    batch_id: str = Field(..., description="批次 ID")
    device_id: str = Field(..., description="边缘设备标识")
    report_time: float = Field(..., description="上报时间戳")
    result_count: int = Field(..., ge=0, description="批次结果数量")
    total_detections: int = Field(..., ge=0, description="批次检测总数")
    created_at: float = Field(..., description="服务端接收时间戳")


class ReportBatchListResponse(BaseModel):
    """边缘上报批次列表响应。"""

    status: str = Field(..., description="查询状态")
    count: int = Field(..., ge=0, description="返回条数")
    items: list[ReportBatchSummaryResponse] = Field(
        default_factory=list,
        description="批次摘要列表",
    )
    request_id: str | None = Field(None, description="请求 ID")


class ReportDeviceSummaryResponse(BaseModel):
    """设备聚合摘要。"""

    device_id: str = Field(..., description="边缘设备标识")
    batch_count: int = Field(..., ge=0, description="累计批次数")
    result_count: int = Field(..., ge=0, description="累计结果数")
    total_detections: int = Field(..., ge=0, description="累计检测总数")
    last_report_time: float = Field(..., description="最近上报时间")
    last_batch_id: str = Field(..., description="最近批次 ID")
    last_created_at: float = Field(..., description="最近服务端接收时间")
    site_name: str = Field("", description="站点名称")
    display_name: str = Field("", description="设备显示名称")
    note: str = Field("", description="设备备注")


class ReportDeviceMetadataRequest(BaseModel):
    """设备元数据写入请求。"""

    site_name: str = Field("", max_length=100, description="站点名称")
    display_name: str = Field("", max_length=100, description="设备显示名称")
    note: str = Field("", max_length=500, description="设备备注")


class ReportDeviceMetadataResponse(BaseModel):
    """设备元数据响应。"""

    device_id: str = Field(..., description="设备标识")
    site_name: str = Field("", description="站点名称")
    display_name: str = Field("", description="设备显示名称")
    note: str = Field("", description="设备备注")
    updated_at: float = Field(..., description="更新时间")


class AlertSummaryResponse(BaseModel):
    """最小告警摘要。"""

    status: str = Field(..., description="摘要状态")
    stale_device_count: int = Field(..., ge=0, description="长时间未上报设备数")
    failed_task_count: int = Field(..., ge=0, description="失败任务数")
    partial_failed_task_count: int = Field(..., ge=0, description="部分失败任务数")
    ready_failure_count: int = Field(..., ge=0, description="就绪检查失败次数")
    request_id: str | None = Field(None, description="请求 ID")


class DetectionReportFindingResponse(BaseModel):
    """模板报告中的单类缺陷发现。"""

    label: str = Field(..., description="缺陷英文标签")
    label_cn: str = Field(..., description="缺陷中文名称")
    count: int = Field(..., ge=0, description="该类缺陷候选数量")
    max_confidence: float = Field(..., ge=0.0, le=1.0, description="最高置信度")
    risk_level: str = Field(..., description="风险等级")
    action: str = Field(..., description="建议动作")


class DetectionReportResponse(BaseModel):
    """基于结构化检测结果生成的模板报告。"""

    title: str = Field(..., description="报告标题")
    summary: str = Field(..., description="报告摘要")
    risk_level: str = Field(..., description="整体风险等级")
    finding_count: int = Field(..., ge=0, description="发现类别数量")
    total_detections: int = Field(..., ge=0, description="缺陷候选总数")
    findings: list[DetectionReportFindingResponse] = Field(
        default_factory=list,
        description="按风险排序的发现项",
    )
    recommendations: list[str] = Field(default_factory=list, description="处置建议")
    llm_context: dict[str, Any] = Field(
        default_factory=dict,
        description="后续接入大模型报告生成的结构化上下文",
    )
    generated_by: Literal["template", "llm"] = Field(..., description="生成方式")
    request_id: str | None = Field(None, description="请求 ID")


class AuditLogResponse(BaseModel):
    """审计日志响应。"""

    event_type: str = Field(..., description="事件类型")
    resource_id: str = Field(..., description="资源标识")
    actor: str = Field(..., description="操作者")
    request_id: str = Field(..., description="请求 ID")
    detail_json: str = Field(..., description="详情 JSON")
    created_at: float = Field(..., description="创建时间")


class ReportDeviceListResponse(BaseModel):
    """设备聚合列表响应。"""

    status: str = Field(..., description="查询状态")
    count: int = Field(..., ge=0, description="返回条数")
    items: list[ReportDeviceSummaryResponse] = Field(
        default_factory=list,
        description="设备聚合摘要列表",
    )
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
