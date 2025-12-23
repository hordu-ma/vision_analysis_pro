"""上报器模块

提供多种结果上报方式的统一接口和工厂函数。

支持的上报器类型：
- http: HTTP/HTTPS 上报（支持重试和离线缓存）
- mqtt: MQTT 上报（待实现）
"""

from ..config import CacheConfig, ReporterConfig
from .base import BaseReporter
from .cache import CacheManager
from .http import HTTPReporter

__all__ = [
    "BaseReporter",
    "CacheManager",
    "HTTPReporter",
    "create_reporter",
]


def create_reporter(
    config: ReporterConfig,
    cache_config: CacheConfig | None = None,
) -> BaseReporter:
    """创建上报器实例

    根据配置中指定的类型创建相应的上报器。

    Args:
        config: 上报器配置
        cache_config: 缓存配置，为 None 则禁用离线缓存

    Returns:
        对应类型的上报器实例

    Raises:
        ValueError: 不支持的上报器类型

    Examples:
        >>> config = ReporterConfig(type="http", url="http://api.example.com/report")
        >>> cache_config = CacheConfig(enabled=True, db_path="cache/agent.db")
        >>> reporter = create_reporter(config, cache_config)
        >>> with reporter:
        ...     status = reporter.report_sync(payload)
    """
    reporter_type = config.type.lower()

    if reporter_type == "http":
        return HTTPReporter(config, cache_config)

    if reporter_type == "mqtt":
        raise NotImplementedError(
            "MQTT 上报器尚未实现，请使用 HTTP 上报器或提交 feature request"
        )

    raise ValueError(
        f"不支持的上报器类型: {reporter_type}，支持的类型: ['http', 'mqtt']"
    )
