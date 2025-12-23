"""摄像头和 RTSP 流数据源

支持从本地摄像头或 RTSP 流读取帧数据。
"""

import logging
import time

import cv2

from ..config import SourceConfig
from ..models import FrameData
from .base import BaseSource

logger = logging.getLogger(__name__)


class CameraSource(BaseSource):
    """摄像头/RTSP 流数据源

    支持本地摄像头（通过设备索引）和 RTSP/HTTP 视频流。

    Examples:
        本地摄像头: path = "0" 或 "1"
        RTSP 流: path = "rtsp://user:pass@192.168.1.100:554/stream"
        HTTP 流: path = "http://192.168.1.100:8080/video"

    Attributes:
        config: 数据源配置
        source_id: 数据源标识符
    """

    def __init__(self, config: SourceConfig, source_id: str = "camera") -> None:
        """初始化摄像头/RTSP 数据源

        Args:
            config: 数据源配置
            source_id: 数据源标识符
        """
        super().__init__(config, source_id)
        self._cap: cv2.VideoCapture | None = None
        self._source: int | str = self._parse_source(config.path)
        self._fps = 0.0
        self._width = 0
        self._height = 0
        self._is_streaming = False

    @staticmethod
    def _parse_source(path: str) -> int | str:
        """解析数据源路径

        Args:
            path: 数据源路径（可以是摄像头索引或 URL）

        Returns:
            摄像头索引（int）或流 URL（str）
        """
        # 尝试解析为摄像头索引
        try:
            return int(path)
        except ValueError:
            # 作为 URL 返回
            return path

    @property
    def is_rtsp(self) -> bool:
        """是否为 RTSP 流"""
        if isinstance(self._source, str):
            return self._source.lower().startswith("rtsp://")
        return False

    @property
    def is_http_stream(self) -> bool:
        """是否为 HTTP 流"""
        if isinstance(self._source, str):
            lower = self._source.lower()
            return lower.startswith("http://") or lower.startswith("https://")
        return False

    @property
    def is_local_camera(self) -> bool:
        """是否为本地摄像头"""
        return isinstance(self._source, int)

    def open(self) -> None:
        """打开摄像头或流

        Raises:
            RuntimeError: 无法打开摄像头或流
        """
        if self._is_open:
            logger.warning(f"摄像头源 {self.source_id} 已经打开")
            return

        # 设置 OpenCV 后端选项
        if self.is_rtsp:
            # RTSP 流使用 FFMPEG 后端
            self._cap = cv2.VideoCapture(self._source, cv2.CAP_FFMPEG)
            # 设置缓冲区大小以减少延迟
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        elif self.is_local_camera:
            # 本地摄像头
            self._cap = cv2.VideoCapture(self._source)
        else:
            # HTTP 流或其他
            self._cap = cv2.VideoCapture(self._source)

        if not self._cap.isOpened():
            source_type = "摄像头" if self.is_local_camera else "流"
            raise RuntimeError(f"无法打开{source_type}: {self._source}")

        # 获取视频属性
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 对于流媒体，FPS 可能为 0
        if self._fps <= 0:
            self._fps = 30.0  # 默认假设 30 fps

        self._is_open = True
        self._is_streaming = True

        source_desc = (
            f"本地摄像头 {self._source}"
            if self.is_local_camera
            else f"流 {self._source}"
        )
        logger.info(
            f"摄像头源 {self.source_id} 已打开: {source_desc} "
            f"({self._width}x{self._height}, {self._fps:.2f} fps)"
        )

    def close(self) -> None:
        """关闭摄像头或流，释放资源"""
        self._is_streaming = False
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_open = False
        logger.info(f"摄像头源 {self.source_id} 已关闭")

    def read_frame(self) -> FrameData | None:
        """读取下一帧

        Returns:
            FrameData 实例，如果读取失败则返回 None
        """
        if not self._is_open or self._cap is None:
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            # 流可能暂时断开，尝试重连
            if self._is_streaming and not self.is_local_camera:
                logger.warning(f"流 {self.source_id} 读取失败，可能需要重连")
            return None

        return FrameData(
            image=frame,
            timestamp=time.time(),
            source_id=self.source_id,
            frame_id=self._frame_count + 1,
            metadata={
                "source": str(self._source),
                "is_rtsp": self.is_rtsp,
                "is_local_camera": self.is_local_camera,
                "resolution": (self._width, self._height),
            },
        )

    def _reset(self) -> None:
        """重置流连接

        对于实时流，重置意味着重新连接。
        """
        if not self.is_local_camera:
            logger.info(f"重新连接流 {self.source_id}")
            self.close()
            self._frame_count = 0
            try:
                self.open()
            except RuntimeError as e:
                logger.error(f"重连失败: {e}")

    def reconnect(self, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
        """尝试重新连接

        Args:
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）

        Returns:
            是否重连成功
        """
        for attempt in range(max_retries):
            try:
                self.close()
                time.sleep(retry_delay)
                self.open()
                logger.info(f"摄像头源 {self.source_id} 重连成功 (尝试 {attempt + 1})")
                return True
            except RuntimeError as e:
                logger.warning(
                    f"摄像头源 {self.source_id} 重连失败 "
                    f"(尝试 {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))

        logger.error(f"摄像头源 {self.source_id} 重连失败，已达到最大重试次数")
        return False

    @property
    def fps(self) -> float:
        """帧率"""
        return self._fps

    @property
    def resolution(self) -> tuple[int, int]:
        """分辨率 (width, height)"""
        return (self._width, self._height)

    @property
    def is_streaming(self) -> bool:
        """是否正在流式传输"""
        return self._is_streaming

    def set_resolution(self, width: int, height: int) -> bool:
        """设置分辨率（仅对本地摄像头有效）

        Args:
            width: 宽度
            height: 高度

        Returns:
            是否设置成功
        """
        if not self.is_local_camera or self._cap is None:
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        # 验证设置是否生效
        actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if actual_width == width and actual_height == height:
            self._width = width
            self._height = height
            logger.info(f"摄像头分辨率已设置为 {width}x{height}")
            return True
        else:
            logger.warning(
                f"无法设置分辨率 {width}x{height}，"
                f"实际分辨率: {actual_width}x{actual_height}"
            )
            return False

    def set_fps(self, fps: float) -> bool:
        """设置帧率（仅对本地摄像头有效）

        Args:
            fps: 目标帧率

        Returns:
            是否设置成功
        """
        if not self.is_local_camera or self._cap is None:
            return False

        self._cap.set(cv2.CAP_PROP_FPS, fps)

        # 验证设置是否生效
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)

        if abs(actual_fps - fps) < 1.0:
            self._fps = actual_fps
            logger.info(f"摄像头帧率已设置为 {actual_fps:.2f}")
            return True
        else:
            logger.warning(f"无法设置帧率 {fps}，实际帧率: {actual_fps:.2f}")
            return False

    def get_info(self) -> dict:
        """获取摄像头源信息"""
        info = super().get_info()
        info.update(
            {
                "source": str(self._source),
                "is_local_camera": self.is_local_camera,
                "is_rtsp": self.is_rtsp,
                "is_http_stream": self.is_http_stream,
                "is_streaming": self._is_streaming,
                "fps": self._fps,
                "resolution": self.resolution,
            }
        )
        return info
