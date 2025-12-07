"""推理引擎基类"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class InferenceEngine(ABC):
    """推理引擎抽象基类"""

    def __init__(self, model_path: str | Path) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

    @abstractmethod
    def predict(self, image: Any, conf: float = 0.5, iou: float = 0.5) -> Any:
        """执行推理

        Args:
            image: 输入图像（numpy数组或路径）
            conf: 置信度阈值
            iou: IoU阈值

        Returns:
            检测结果
        """
        pass

    @abstractmethod
    def warmup(self, imgsz: int = 640) -> None:
        """预热模型"""
        pass
