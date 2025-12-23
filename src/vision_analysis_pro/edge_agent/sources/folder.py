"""图像文件夹数据源

支持从本地文件夹中读取图像文件，按文件名排序逐个处理。
"""

import logging
import time
from pathlib import Path

import cv2

from ..config import SourceConfig
from ..models import FrameData
from .base import BaseSource

logger = logging.getLogger(__name__)


class FolderSource(BaseSource):
    """图像文件夹数据源

    从本地文件夹中逐个读取图像文件。
    支持 JPG、PNG、BMP 等常见图像格式。

    Attributes:
        config: 数据源配置
        source_id: 数据源标识符
    """

    def __init__(self, config: SourceConfig, source_id: str = "folder") -> None:
        """初始化文件夹数据源

        Args:
            config: 数据源配置
            source_id: 数据源标识符
        """
        super().__init__(config, source_id)
        self._folder_path = Path(config.path)
        self._image_files: list[Path] = []
        self._current_index = 0

    def open(self) -> None:
        """打开文件夹，扫描图像文件

        Raises:
            FileNotFoundError: 文件夹不存在
            ValueError: 文件夹为空或不包含支持的图像文件
        """
        if self._is_open:
            logger.warning(f"文件夹源 {self.source_id} 已经打开")
            return

        # 检查文件夹存在性
        if not self._folder_path.exists():
            raise FileNotFoundError(f"文件夹不存在: {self._folder_path}")

        if not self._folder_path.is_dir():
            raise ValueError(f"路径不是文件夹: {self._folder_path}")

        # 扫描图像文件
        extensions = {ext.lower() for ext in self.config.extensions}
        self._image_files = sorted(
            [
                f
                for f in self._folder_path.iterdir()
                if f.is_file() and f.suffix.lower() in extensions
            ]
        )

        if not self._image_files:
            raise ValueError(
                f"文件夹中没有支持的图像文件: {self._folder_path}, "
                f"支持的扩展名: {extensions}"
            )

        self._current_index = 0
        self._is_open = True
        logger.info(
            f"文件夹源 {self.source_id} 已打开: {self._folder_path} "
            f"(共 {len(self._image_files)} 个图像文件)"
        )

    def close(self) -> None:
        """关闭文件夹数据源"""
        self._image_files = []
        self._current_index = 0
        self._is_open = False
        logger.info(f"文件夹源 {self.source_id} 已关闭")

    def read_frame(self) -> FrameData | None:
        """读取下一个图像文件

        Returns:
            FrameData 实例，如果所有图像已读取则返回 None
        """
        if not self._is_open:
            return None

        if self._current_index >= len(self._image_files):
            return None

        image_path = self._image_files[self._current_index]
        self._current_index += 1

        # 读取图像
        image = cv2.imread(str(image_path))
        if image is None:
            logger.warning(f"无法读取图像文件: {image_path}，跳过")
            # 递归读取下一个
            return self.read_frame()

        return FrameData(
            image=image,
            timestamp=time.time(),
            source_id=self.source_id,
            frame_id=self._current_index,
            metadata={
                "image_path": str(image_path),
                "image_name": image_path.name,
                "folder_path": str(self._folder_path),
                "total_images": len(self._image_files),
                "current_index": self._current_index,
            },
        )

    def _reset(self) -> None:
        """重置到文件夹开头以支持循环"""
        self._current_index = 0
        self._frame_count = 0
        logger.debug(f"文件夹源 {self.source_id} 已重置到开头")

    @property
    def total_images(self) -> int:
        """文件夹中的图像总数"""
        return len(self._image_files)

    @property
    def current_index(self) -> int:
        """当前图像索引"""
        return self._current_index

    @property
    def progress(self) -> float:
        """读取进度 [0.0, 1.0]"""
        if self.total_images > 0:
            return self._current_index / self.total_images
        return 0.0

    @property
    def remaining(self) -> int:
        """剩余未读取的图像数"""
        return max(0, self.total_images - self._current_index)

    @property
    def image_files(self) -> list[Path]:
        """图像文件列表（只读）"""
        return self._image_files.copy()

    def get_info(self) -> dict:
        """获取文件夹源信息"""
        info = super().get_info()
        info.update(
            {
                "folder_path": str(self._folder_path),
                "total_images": self.total_images,
                "current_index": self._current_index,
                "progress": self.progress,
                "remaining": self.remaining,
                "extensions": self.config.extensions,
            }
        )
        return info
