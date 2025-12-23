"""边缘推理 Agent 模块

提供边缘设备上的实时视频/图像推理能力，支持：
- 多种数据源（视频文件、图像文件夹、摄像头、RTSP 流）
- 多种推理引擎（ONNX Runtime、Ultralytics YOLO）
- HTTP 上报（含重试和离线缓存）
- 灵活的配置（YAML + 环境变量）

Usage:
    # 使用配置文件启动
    agent = EdgeAgent(config_path="config.yaml")
    agent.run()

    # 使用配置对象启动
    config = EdgeAgentConfig.load("config.yaml")
    agent = EdgeAgent(config=config)
    agent.run()

    # 命令行启动
    $ edge-agent -c config.yaml
"""

from .agent import EdgeAgent, main
from .config import (
    CacheConfig,
    EdgeAgentConfig,
    InferenceConfig,
    ReporterConfig,
    SourceConfig,
)
from .models import (
    CacheEntry,
    Detection,
    FrameData,
    InferenceResult,
    ReportPayload,
    ReportStatus,
    SourceType,
)

__version__ = "0.1.0"

__all__ = [
    # Agent
    "EdgeAgent",
    "main",
    # Config
    "EdgeAgentConfig",
    "SourceConfig",
    "InferenceConfig",
    "ReporterConfig",
    "CacheConfig",
    # Models
    "FrameData",
    "Detection",
    "InferenceResult",
    "ReportPayload",
    "ReportStatus",
    "SourceType",
    "CacheEntry",
]
