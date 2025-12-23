"""视频文件数据源

支持从本地视频文件（MP4、AVI 等）读取帧数据。
"""

import logging
import time
from pathlib import Path

import cv2

from ..config import SourceConfig
from ..models import FrameData
from .base import BaseSource

logger = logging.getLogger(__name__)


class VideoSource(BaseSource):
    """视频文件数据源

    从本地视频文件中逐帧读取图像数据。
    支持多种视频格式（取决于 OpenCV 编译时的支持）。

    Attributes:
        config: 数据源配置
        source_id: 数据源标识符
    """

    # 支持的视频文件扩展名
    SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}

    def __init__(self, config: SourceConfig, source_id: str = "video") -> None:
        """初始化视频数据源

        Args:
            config: 数据源配置
            source_id: 数据源标识符
        """
        super().__init__(config, source_id)
        self._cap: cv2.VideoCapture | None = None
        self._video_path = Path(config.path)
        self._total_frames = 0
        self._fps = 0.0
        self._width = 0
        self._height = 0

    def open(self) -> None:
        """打开视频文件

        Raises:
            FileNotFoundError: 视频文件不存在
            ValueError: 不支持的视频格式
            RuntimeError: 无法打开视频文件
        """
        if self._is_open:
            logger.warning(f"视频源 {self.source_id} 已经打开")
            return

        # 检查文件存在性
        if not self._video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {self._video_path}")

        # 检查文件扩展名
        ext = self._video_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"不支持的视频格式: {ext}，支持的格式: {self.SUPPORTED_EXTENSIONS}"
            )

        # 打开视频
        self._cap = cv2.VideoCapture(str(self._video_path))
        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {self._video_path}")

        # 获取视频属性
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self._is_open = True
        logger.info(
            f"视频源 {self.source_id} 已打开: {self._video_path} "
            f"({self._width}x{self._height}, {self._fps:.2f} fps, "
            f"{self._total_frames} frames)"
        )

    def close(self) -> None:
        """关闭视频文件，释放资源"""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_open = False
        logger.info(f"视频源 {self.source_id} 已关闭")

    def read_frame(self) -> FrameData | None:
        """读取下一帧

        Returns:
            FrameData 实例，如果视频结束则返回 None
        """
        if not self._is_open or self._cap is None:
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None

        # 获取当前帧位置
        current_frame = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))

        return FrameData(
            image=frame,
            timestamp=time.time(),
            source_id=self.source_id,
            frame_id=current_frame,
            metadata={
                "video_path": str(self._video_path),
                "video_frame": current_frame,
                "total_frames": self._total_frames,
                "original_fps": self._fps,
            },
        )

    def _reset(self) -> None:
        """重置视频到开头以支持循环播放"""
        if self._cap is not None:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._frame_count = 0
            logger.debug(f"视频源 {self.source_id} 已重置到开头")

    def seek(self, frame_number: int) -> bool:
        """跳转到指定帧

        Args:
            frame_number: 目标帧号

        Returns:
            是否跳转成功
        """
        if not self._is_open or self._cap is None:
            return False

        if frame_number < 0 or frame_number >= self._total_frames:
            logger.warning(
                f"帧号超出范围: {frame_number}, 有效范围: [0, {self._total_frames - 1}]"
            )
            return False

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        return True

    def seek_time(self, seconds: float) -> bool:
        """跳转到指定时间

        Args:
            seconds: 目标时间（秒）

        Returns:
            是否跳转成功
        """
        if self._fps <= 0:
            return False

        frame_number = int(seconds * self._fps)
        return self.seek(frame_number)

    @property
    def total_frames(self) -> int:
        """视频总帧数"""
        return self._total_frames

    @property
    def fps(self) -> float:
        """视频原始帧率"""
        return self._fps

    @property
    def duration(self) -> float:
        """视频时长（秒）"""
        if self._fps > 0:
            return self._total_frames / self._fps
        return 0.0

    @property
    def resolution(self) -> tuple[int, int]:
        """视频分辨率 (width, height)"""
        return (self._width, self._height)

    @property
    def current_position(self) -> int:
        """当前帧位置"""
        if self._cap is not None:
            return int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
        return 0

    @property
    def progress(self) -> float:
        """播放进度 [0.0, 1.0]"""
        if self._total_frames > 0:
            return self.current_position / self._total_frames
        return 0.0

    def get_info(self) -> dict:
        """获取视频源信息"""
        info = super().get_info()
        info.update(
            {
                "video_path": str(self._video_path),
                "total_frames": self._total_frames,
                "fps": self._fps,
                "duration": self.duration,
                "resolution": self.resolution,
                "current_position": self.current_position,
                "progress": self.progress,
            }
        )
        return info
