"""数据源模块

提供多种数据采集源的统一接口和工厂函数。

支持的数据源类型：
- video: 本地视频文件
- folder: 图像文件夹
- camera: 本地摄像头
- rtsp: RTSP 视频流
"""

from ..config import SourceConfig
from ..models import SourceType
from .base import BaseSource
from .camera import CameraSource
from .folder import FolderSource
from .video import VideoSource

__all__ = [
    "BaseSource",
    "CameraSource",
    "FolderSource",
    "VideoSource",
    "create_source",
]


def create_source(config: SourceConfig, source_id: str = "default") -> BaseSource:
    """创建数据源实例

    根据配置中指定的类型创建相应的数据源。

    Args:
        config: 数据源配置
        source_id: 数据源标识符

    Returns:
        对应类型的数据源实例

    Raises:
        ValueError: 不支持的数据源类型

    Examples:
        >>> config = SourceConfig(type=SourceType.VIDEO, path="video.mp4")
        >>> source = create_source(config, "my-video")
        >>> with source:
        ...     for frame in source:
        ...         process(frame)
    """
    source_type = config.type

    if source_type == SourceType.VIDEO:
        return VideoSource(config, source_id)

    if source_type == SourceType.FOLDER:
        return FolderSource(config, source_id)

    if source_type in (SourceType.CAMERA, SourceType.RTSP):
        return CameraSource(config, source_id)

    raise ValueError(
        f"不支持的数据源类型: {source_type}，支持的类型: {list(SourceType)}"
    )
