"""边缘 Agent 数据模型定义"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np


class SourceType(str, Enum):
    """数据源类型"""

    VIDEO = "video"
    RTSP = "rtsp"
    FOLDER = "folder"
    CAMERA = "camera"


class ReportStatus(str, Enum):
    """上报状态"""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class FrameData:
    """帧数据

    Attributes:
        image: 图像数据 (HxWxC, BGR 格式)
        timestamp: 采集时间戳 (UNIX 时间戳)
        source_id: 数据源标识
        frame_id: 帧序号
        metadata: 额外元数据
    """

    image: np.ndarray
    timestamp: float
    source_id: str
    frame_id: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def datetime(self) -> datetime:
        """获取采集时间的 datetime 对象"""
        return datetime.fromtimestamp(self.timestamp)

    @property
    def shape(self) -> tuple[int, ...]:
        """获取图像尺寸"""
        return self.image.shape


@dataclass
class Detection:
    """单个检测结果

    Attributes:
        label: 类别名称
        confidence: 置信度 [0.0, 1.0]
        bbox: 边界框 [x1, y1, x2, y2] 像素坐标
    """

    label: str
    confidence: float
    bbox: list[float]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "label": self.label,
            "confidence": self.confidence,
            "bbox": self.bbox,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Detection":
        """从字典创建"""
        return cls(
            label=data["label"],
            confidence=data["confidence"],
            bbox=data["bbox"],
        )


@dataclass
class InferenceResult:
    """推理结果

    Attributes:
        frame_id: 对应的帧序号
        timestamp: 推理完成时间戳
        source_id: 数据源标识
        detections: 检测结果列表
        inference_time_ms: 推理耗时 (毫秒)
        metadata: 额外元数据
    """

    frame_id: int
    timestamp: float
    source_id: str
    detections: list[Detection]
    inference_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_detections(self) -> bool:
        """是否有检测结果"""
        return len(self.detections) > 0

    @property
    def detection_count(self) -> int:
        """检测数量"""
        return len(self.detections)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "source_id": self.source_id,
            "detections": [d.to_dict() for d in self.detections],
            "inference_time_ms": self.inference_time_ms,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InferenceResult":
        """从字典创建"""
        return cls(
            frame_id=data["frame_id"],
            timestamp=data["timestamp"],
            source_id=data["source_id"],
            detections=[Detection.from_dict(d) for d in data["detections"]],
            inference_time_ms=data.get("inference_time_ms", 0.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ReportPayload:
    """上报数据载荷

    Attributes:
        device_id: 设备标识
        results: 推理结果列表
        report_time: 上报时间戳
        batch_id: 批次 ID
        status: 上报状态
        retry_count: 重试次数
    """

    device_id: str
    results: list[InferenceResult]
    report_time: float = field(default_factory=lambda: datetime.now().timestamp())
    batch_id: str = ""
    status: ReportStatus = ReportStatus.PENDING
    retry_count: int = 0

    def __post_init__(self) -> None:
        """初始化后处理"""
        if not self.batch_id:
            # 生成批次 ID: device_id-timestamp
            self.batch_id = f"{self.device_id}-{int(self.report_time * 1000)}"

    def to_dict(self) -> dict[str, Any]:
        """转换为可 JSON 序列化的字典"""
        return {
            "device_id": self.device_id,
            "batch_id": self.batch_id,
            "report_time": self.report_time,
            "results": [r.to_dict() for r in self.results],
        }

    @property
    def result_count(self) -> int:
        """结果数量"""
        return len(self.results)

    @property
    def total_detections(self) -> int:
        """总检测数量"""
        return sum(r.detection_count for r in self.results)


@dataclass
class CacheEntry:
    """缓存条目

    用于离线缓存时存储待上报的数据

    Attributes:
        id: 缓存条目 ID
        payload: 上报载荷
        created_at: 创建时间
        retry_count: 已重试次数
        last_error: 最后一次错误信息
    """

    id: int
    payload: ReportPayload
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    retry_count: int = 0
    last_error: str = ""

    @property
    def age_seconds(self) -> float:
        """缓存时长 (秒)"""
        return datetime.now().timestamp() - self.created_at
