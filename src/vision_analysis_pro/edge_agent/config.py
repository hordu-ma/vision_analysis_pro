"""边缘 Agent 配置管理

支持从 YAML 文件和环境变量加载配置，环境变量优先级更高。
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .models import SourceType

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """数据源配置

    Attributes:
        type: 数据源类型 (video, rtsp, folder, camera)
        path: 数据源路径或 URL
        fps_limit: 帧率限制，0 表示不限制
        loop: 是否循环播放（仅对视频和文件夹有效）
        skip_frames: 跳帧数，0 表示不跳帧
        extensions: 支持的图像扩展名（仅对文件夹有效）
    """

    type: SourceType = SourceType.VIDEO
    path: str = "0"  # 默认使用第一个摄像头
    fps_limit: float = 0.0
    loop: bool = False
    skip_frames: int = 0
    extensions: list[str] = field(
        default_factory=lambda: [".jpg", ".jpeg", ".png", ".bmp"]
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceConfig":
        """从字典创建配置"""
        source_type = data.get("type", "video")
        if isinstance(source_type, str):
            source_type = SourceType(source_type)

        return cls(
            type=source_type,
            path=str(data.get("path", "0")),
            fps_limit=float(data.get("fps_limit", 0.0)),
            loop=bool(data.get("loop", False)),
            skip_frames=int(data.get("skip_frames", 0)),
            extensions=data.get("extensions", [".jpg", ".jpeg", ".png", ".bmp"]),
        )


@dataclass
class InferenceConfig:
    """推理配置

    Attributes:
        engine: 推理引擎类型 (onnx, yolo)
        model_path: 模型文件路径
        confidence: 置信度阈值
        iou: IoU 阈值
        device: 推理设备 (cpu, cuda, mps)
        warmup: 是否预热模型
    """

    engine: str = "onnx"
    model_path: str = "models/best.onnx"
    confidence: float = 0.5
    iou: float = 0.5
    device: str = "cpu"
    warmup: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InferenceConfig":
        """从字典创建配置"""
        return cls(
            engine=str(data.get("engine", "onnx")),
            model_path=str(data.get("model_path", "models/best.onnx")),
            confidence=float(data.get("confidence", 0.5)),
            iou=float(data.get("iou", 0.5)),
            device=str(data.get("device", "cpu")),
            warmup=bool(data.get("warmup", True)),
        )


@dataclass
class ReporterConfig:
    """上报器配置

    Attributes:
        type: 上报器类型 (http, mqtt)
        url: 上报地址
        api_key: API 密钥（从环境变量注入）
        timeout: 请求超时 (秒)
        retry_max: 最大重试次数
        retry_delay: 重试初始延迟 (秒)
        retry_backoff: 重试退避倍数
        batch_size: 批量上报大小
        batch_interval: 批量上报间隔 (秒)
    """

    type: str = "http"
    url: str = "http://localhost:8000/api/v1/report"
    api_key: str = ""
    timeout: float = 30.0
    retry_max: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    batch_size: int = 10
    batch_interval: float = 5.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReporterConfig":
        """从字典创建配置"""
        return cls(
            type=str(data.get("type", "http")),
            url=str(data.get("url", "http://localhost:8000/api/v1/report")),
            api_key=str(data.get("api_key", "")),
            timeout=float(data.get("timeout", 30.0)),
            retry_max=int(data.get("retry_max", 3)),
            retry_delay=float(data.get("retry_delay", 1.0)),
            retry_backoff=float(data.get("retry_backoff", 2.0)),
            batch_size=int(data.get("batch_size", 10)),
            batch_interval=float(data.get("batch_interval", 5.0)),
        )


@dataclass
class CacheConfig:
    """离线缓存配置

    Attributes:
        enabled: 是否启用离线缓存
        db_path: SQLite 数据库路径
        max_entries: 最大缓存条目数
        max_age_hours: 最大缓存时长 (小时)
        flush_interval: 缓存刷新间隔 (秒)
    """

    enabled: bool = True
    db_path: str = "cache/edge_agent.db"
    max_entries: int = 10000
    max_age_hours: float = 24.0
    flush_interval: float = 60.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheConfig":
        """从字典创建配置"""
        return cls(
            enabled=bool(data.get("enabled", True)),
            db_path=str(data.get("db_path", "cache/edge_agent.db")),
            max_entries=int(data.get("max_entries", 10000)),
            max_age_hours=float(data.get("max_age_hours", 24.0)),
            flush_interval=float(data.get("flush_interval", 60.0)),
        )


@dataclass
class EdgeAgentConfig:
    """边缘 Agent 主配置

    Attributes:
        device_id: 设备唯一标识
        log_level: 日志级别
        source: 数据源配置
        inference: 推理配置
        reporter: 上报器配置
        cache: 缓存配置
        report_only_detections: 仅上报有检测结果的帧
    """

    device_id: str = "edge-agent-001"
    log_level: str = "INFO"
    source: SourceConfig = field(default_factory=SourceConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    reporter: ReporterConfig = field(default_factory=ReporterConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    report_only_detections: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EdgeAgentConfig":
        """从字典创建配置"""
        return cls(
            device_id=str(data.get("device_id", "edge-agent-001")),
            log_level=str(data.get("log_level", "INFO")),
            source=SourceConfig.from_dict(data.get("source", {})),
            inference=InferenceConfig.from_dict(data.get("inference", {})),
            reporter=ReporterConfig.from_dict(data.get("reporter", {})),
            cache=CacheConfig.from_dict(data.get("cache", {})),
            report_only_detections=bool(data.get("report_only_detections", True)),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "EdgeAgentConfig":
        """从 YAML 文件加载配置

        Args:
            path: YAML 配置文件路径

        Returns:
            EdgeAgentConfig 实例

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 解析错误
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        logger.info(f"从 YAML 加载配置: {config_path}")
        return cls.from_dict(data)

    @classmethod
    def from_env(cls, prefix: str = "EDGE_AGENT") -> "EdgeAgentConfig":
        """从环境变量加载配置

        环境变量命名规则: {prefix}_{SECTION}_{KEY}
        例如: EDGE_AGENT_DEVICE_ID, EDGE_AGENT_SOURCE_TYPE

        Args:
            prefix: 环境变量前缀

        Returns:
            EdgeAgentConfig 实例
        """
        data: dict[str, Any] = {}

        # 顶层配置
        if env_val := os.getenv(f"{prefix}_DEVICE_ID"):
            data["device_id"] = env_val
        if env_val := os.getenv(f"{prefix}_LOG_LEVEL"):
            data["log_level"] = env_val
        if env_val := os.getenv(f"{prefix}_REPORT_ONLY_DETECTIONS"):
            data["report_only_detections"] = env_val.lower() in ("true", "1", "yes")

        # 数据源配置
        source_data: dict[str, Any] = {}
        if env_val := os.getenv(f"{prefix}_SOURCE_TYPE"):
            source_data["type"] = env_val
        if env_val := os.getenv(f"{prefix}_SOURCE_PATH"):
            source_data["path"] = env_val
        if env_val := os.getenv(f"{prefix}_SOURCE_FPS_LIMIT"):
            source_data["fps_limit"] = float(env_val)
        if env_val := os.getenv(f"{prefix}_SOURCE_LOOP"):
            source_data["loop"] = env_val.lower() in ("true", "1", "yes")
        if env_val := os.getenv(f"{prefix}_SOURCE_SKIP_FRAMES"):
            source_data["skip_frames"] = int(env_val)
        if source_data:
            data["source"] = source_data

        # 推理配置
        inference_data: dict[str, Any] = {}
        if env_val := os.getenv(f"{prefix}_INFERENCE_ENGINE"):
            inference_data["engine"] = env_val
        if env_val := os.getenv(f"{prefix}_INFERENCE_MODEL_PATH"):
            inference_data["model_path"] = env_val
        if env_val := os.getenv(f"{prefix}_INFERENCE_CONFIDENCE"):
            inference_data["confidence"] = float(env_val)
        if env_val := os.getenv(f"{prefix}_INFERENCE_IOU"):
            inference_data["iou"] = float(env_val)
        if env_val := os.getenv(f"{prefix}_INFERENCE_DEVICE"):
            inference_data["device"] = env_val
        if inference_data:
            data["inference"] = inference_data

        # 上报器配置
        reporter_data: dict[str, Any] = {}
        if env_val := os.getenv(f"{prefix}_REPORTER_TYPE"):
            reporter_data["type"] = env_val
        if env_val := os.getenv(f"{prefix}_REPORTER_URL"):
            reporter_data["url"] = env_val
        if env_val := os.getenv(f"{prefix}_REPORTER_API_KEY"):
            reporter_data["api_key"] = env_val
        if env_val := os.getenv(f"{prefix}_REPORTER_TIMEOUT"):
            reporter_data["timeout"] = float(env_val)
        if env_val := os.getenv(f"{prefix}_REPORTER_RETRY_MAX"):
            reporter_data["retry_max"] = int(env_val)
        if env_val := os.getenv(f"{prefix}_REPORTER_BATCH_SIZE"):
            reporter_data["batch_size"] = int(env_val)
        if reporter_data:
            data["reporter"] = reporter_data

        # 缓存配置
        cache_data: dict[str, Any] = {}
        if env_val := os.getenv(f"{prefix}_CACHE_ENABLED"):
            cache_data["enabled"] = env_val.lower() in ("true", "1", "yes")
        if env_val := os.getenv(f"{prefix}_CACHE_DB_PATH"):
            cache_data["db_path"] = env_val
        if env_val := os.getenv(f"{prefix}_CACHE_MAX_ENTRIES"):
            cache_data["max_entries"] = int(env_val)
        if cache_data:
            data["cache"] = cache_data

        logger.info(f"从环境变量加载配置 (前缀: {prefix})")
        return cls.from_dict(data)

    @classmethod
    def load(
        cls,
        config_path: str | Path | None = None,
        env_prefix: str = "EDGE_AGENT",
    ) -> "EdgeAgentConfig":
        """加载配置 (YAML + 环境变量)

        优先级: 环境变量 > YAML 配置文件 > 默认值

        Args:
            config_path: YAML 配置文件路径，为 None 则仅从环境变量加载
            env_prefix: 环境变量前缀

        Returns:
            EdgeAgentConfig 实例
        """
        # 从 YAML 加载基础配置
        if config_path:
            base_config = cls.from_yaml(config_path)
            base_data = _config_to_dict(base_config)
        else:
            base_data = {}

        # 从环境变量加载覆盖配置
        env_config = cls.from_env(env_prefix)
        env_data = _config_to_dict(env_config)

        # 深度合并配置 (环境变量覆盖 YAML)
        merged_data = _deep_merge(base_data, env_data)

        logger.info("配置加载完成")
        return cls.from_dict(merged_data)

    def validate(self) -> list[str]:
        """验证配置有效性

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors: list[str] = []

        # 验证置信度阈值
        if not 0.0 <= self.inference.confidence <= 1.0:
            errors.append(
                f"置信度阈值必须在 [0.0, 1.0] 范围内: {self.inference.confidence}"
            )

        # 验证 IoU 阈值
        if not 0.0 <= self.inference.iou <= 1.0:
            errors.append(f"IoU 阈值必须在 [0.0, 1.0] 范围内: {self.inference.iou}")

        # 验证模型文件存在性
        model_path = Path(self.inference.model_path)
        if not model_path.exists():
            errors.append(f"模型文件不存在: {model_path}")

        # 验证数据源路径（非摄像头情况）
        if self.source.type in (SourceType.VIDEO, SourceType.FOLDER):
            source_path = Path(self.source.path)
            if not source_path.exists():
                errors.append(f"数据源路径不存在: {source_path}")

        # 验证上报器配置
        if self.reporter.retry_max < 0:
            errors.append(f"最大重试次数不能为负: {self.reporter.retry_max}")

        if self.reporter.timeout <= 0:
            errors.append(f"请求超时必须大于 0: {self.reporter.timeout}")

        return errors


def _config_to_dict(config: EdgeAgentConfig) -> dict[str, Any]:
    """将配置对象转换为字典"""
    return {
        "device_id": config.device_id,
        "log_level": config.log_level,
        "report_only_detections": config.report_only_detections,
        "source": {
            "type": config.source.type.value,
            "path": config.source.path,
            "fps_limit": config.source.fps_limit,
            "loop": config.source.loop,
            "skip_frames": config.source.skip_frames,
            "extensions": config.source.extensions,
        },
        "inference": {
            "engine": config.inference.engine,
            "model_path": config.inference.model_path,
            "confidence": config.inference.confidence,
            "iou": config.inference.iou,
            "device": config.inference.device,
            "warmup": config.inference.warmup,
        },
        "reporter": {
            "type": config.reporter.type,
            "url": config.reporter.url,
            "api_key": config.reporter.api_key,
            "timeout": config.reporter.timeout,
            "retry_max": config.reporter.retry_max,
            "retry_delay": config.reporter.retry_delay,
            "retry_backoff": config.reporter.retry_backoff,
            "batch_size": config.reporter.batch_size,
            "batch_interval": config.reporter.batch_interval,
        },
        "cache": {
            "enabled": config.cache.enabled,
            "db_path": config.cache.db_path,
            "max_entries": config.cache.max_entries,
            "max_age_hours": config.cache.max_age_hours,
            "flush_interval": config.cache.flush_interval,
        },
    }


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """深度合并两个字典，override 中的非空值覆盖 base

    Args:
        base: 基础字典
        override: 覆盖字典

    Returns:
        合并后的字典
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        elif value is not None and value != "":
            # 只有非空值才覆盖
            result[key] = value

    return result
