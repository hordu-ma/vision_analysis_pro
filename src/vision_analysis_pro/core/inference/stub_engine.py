"""Stub 推理引擎（用于测试和演示）

不依赖真实模型，返回固定/可控的检测结果。
支持场景：
- 正常检测结果（固定 bbox）
- 空结果（无检测对象）
- 模拟异常（如模型未加载）
"""

from pathlib import Path
from typing import Any


class StubInferenceEngine:
    """Stub 推理引擎

    不继承 InferenceEngine，避免强制要求模型路径必须存在。
    提供与真实引擎一致的接口，用于 demo 和测试。
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        mode: str = "normal",
    ) -> None:
        """初始化 stub 引擎

        Args:
            model_path: 模型路径（可选，stub 不实际使用）
            mode: 模式选择
                - "normal": 返回固定检测结果
                - "empty": 返回空结果
                - "error": 模拟推理失败（在 predict 时抛出）
        """
        self.model_path = Path(model_path) if model_path else Path("models/stub.pt")
        self.mode = mode

    def predict(
        self,
        image: object,
        conf: float = 0.5,
        iou: float = 0.5,  # noqa: ANN401
    ) -> list[dict[str, Any]]:
        """执行推理（返回固定结果）

        Args:
            image: 输入图像（任意类型，stub 不实际处理）
            conf: 置信度阈值（用于过滤固定结果）
            iou: IoU阈值（stub 忽略）

        Returns:
            检测结果列表，每项包含 label/confidence/bbox
        """
        if self.mode == "error":
            raise RuntimeError("模拟：推理失败")

        if self.mode == "empty":
            return []

        # 正常模式：返回固定的检测结果
        stub_results = [
            {
                "label": "crack",
                "confidence": 0.95,
                "bbox": [100.0, 150.0, 300.0, 400.0],
            },
            {
                "label": "rust",
                "confidence": 0.88,
                "bbox": [450.0, 200.0, 550.0, 350.0],
            },
            {
                "label": "deformation",
                "confidence": 0.72,
                "bbox": [200.0, 500.0, 400.0, 650.0],
            },
        ]

        # 根据置信度阈值过滤
        return [item for item in stub_results if item["confidence"] >= conf]

    def warmup(self, imgsz: int = 640) -> None:
        """预热模型（stub 无操作）"""
        pass
