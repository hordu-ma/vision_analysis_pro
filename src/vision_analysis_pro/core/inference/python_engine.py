"""Python 推理引擎实现（基于 Ultralytics YOLO）"""

from pathlib import Path
from typing import Any

from .base import InferenceEngine


class PythonInferenceEngine(InferenceEngine):
    """基于 Ultralytics YOLO 的 Python 推理引擎"""

    def __init__(self, model_path: str | Path) -> None:
        super().__init__(model_path)
        # 延迟导入，避免未安装时报错
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ImportError("需要安装 ultralytics: uv pip install ultralytics") from e

        self.model = YOLO(str(self.model_path))

    def predict(self, image: Any, conf: float = 0.5, iou: float = 0.5) -> Any:
        """执行推理"""
        results = self.model(image, conf=conf, iou=iou, verbose=False)
        return results

    def warmup(self, imgsz: int = 640) -> None:
        """预热模型"""
        self.model.warmup(imgsz=imgsz)
