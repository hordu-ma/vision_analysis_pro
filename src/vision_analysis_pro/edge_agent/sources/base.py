"""数据源抽象基类

定义数据采集源的统一接口，支持视频、RTSP、图像文件夹等多种输入方式。
"""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from types import TracebackType

from ..config import SourceConfig
from ..models import FrameData

logger = logging.getLogger(__name__)


class BaseSource(ABC):
    """数据源抽象基类

    所有数据源实现都应继承此类，并实现相应的抽象方法。
    支持上下文管理器协议，确保资源正确释放。
    """

    def __init__(self, config: SourceConfig, source_id: str = "default") -> None:
        """初始化数据源

        Args:
            config: 数据源配置
            source_id: 数据源标识符
        """
        self.config = config
        self.source_id = source_id
        self._frame_count = 0
        self._is_open = False
        self._last_frame_time = 0.0

    @property
    def frame_count(self) -> int:
        """已读取的帧数"""
        return self._frame_count

    @property
    def is_open(self) -> bool:
        """数据源是否已打开"""
        return self._is_open

    @abstractmethod
    def open(self) -> None:
        """打开数据源

        Raises:
            RuntimeError: 打开数据源失败
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭数据源，释放资源"""
        pass

    @abstractmethod
    def read_frame(self) -> FrameData | None:
        """读取下一帧

        Returns:
            FrameData 实例，如果没有更多帧则返回 None
        """
        pass

    def __enter__(self) -> "BaseSource":
        """上下文管理器入口"""
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """上下文管理器出口"""
        self.close()

    def __iter__(self) -> Iterator[FrameData]:
        """迭代器接口，逐帧返回数据"""
        while self._is_open:
            # FPS 限制
            if self.config.fps_limit > 0:
                min_interval = 1.0 / self.config.fps_limit
                elapsed = time.time() - self._last_frame_time
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)

            frame = self.read_frame()
            if frame is None:
                # 检查是否需要循环
                if self.config.loop:
                    logger.info(f"数据源 {self.source_id} 循环重新开始")
                    self._reset()
                    continue
                else:
                    logger.info(f"数据源 {self.source_id} 已结束")
                    break

            self._frame_count += 1
            self._last_frame_time = time.time()

            # 跳帧处理
            if self.config.skip_frames > 0:
                if (self._frame_count - 1) % (self.config.skip_frames + 1) != 0:
                    continue

            yield frame

    def _reset(self) -> None:
        """重置数据源以支持循环播放

        子类可以重写此方法以实现特定的重置逻辑。
        默认实现是关闭并重新打开数据源。
        """
        self.close()
        self._frame_count = 0
        self.open()

    def get_info(self) -> dict:
        """获取数据源信息

        Returns:
            包含数据源元信息的字典
        """
        return {
            "source_id": self.source_id,
            "type": self.config.type.value,
            "path": self.config.path,
            "frame_count": self._frame_count,
            "is_open": self._is_open,
            "fps_limit": self.config.fps_limit,
            "loop": self.config.loop,
            "skip_frames": self.config.skip_frames,
        }
