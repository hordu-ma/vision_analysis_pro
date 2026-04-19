"""Hugging Face 裂缝检测推理引擎。"""

from io import BytesIO
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image

from .base import InferenceEngine


class HFCrackInferenceEngine(InferenceEngine):
    """基于 Hugging Face Object Detection 模型的裂缝检测引擎。"""

    def __init__(self, model_path: str | Path) -> None:
        super().__init__(model_path)
        try:
            from transformers import AutoImageProcessor, AutoModelForObjectDetection
        except ImportError as e:
            msg = "需要安装 transformers 和 huggingface_hub 才能使用 HF 裂缝模型"
            raise ImportError(msg) from e

        self.processor = AutoImageProcessor.from_pretrained(str(self.model_path))
        self.model = AutoModelForObjectDetection.from_pretrained(str(self.model_path))
        self.model.eval()
        self.class_names = {
            int(idx): str(label).lower()
            for idx, label in self.model.config.id2label.items()
        }
        self.num_classes = len(self.class_names)

    def predict(
        self, image: Any, conf: float = 0.5, iou: float = 0.5
    ) -> list[dict[str, Any]]:
        del iou
        if not (0.0 <= conf <= 1.0):
            msg = f"置信度阈值应在 [0.0, 1.0] 范围内，实际: {conf}"
            raise ValueError(msg)

        pil_image = self._to_pil_image(image)
        inputs = self.processor(images=pil_image, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)

        target_sizes = torch.tensor([[pil_image.height, pil_image.width]])
        processed = self.processor.post_process_object_detection(
            outputs,
            threshold=conf,
            target_sizes=target_sizes,
        )[0]

        detections: list[dict[str, Any]] = []
        for score, label, box in zip(
            processed["scores"], processed["labels"], processed["boxes"], strict=True
        ):
            class_id = int(label.item())
            detections.append(
                {
                    "label": self.class_names.get(class_id, f"class_{class_id}"),
                    "confidence": float(score.item()),
                    "bbox": [float(coord) for coord in box.tolist()],
                }
            )

        return detections

    def warmup(self, imgsz: int = 640) -> None:
        dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
        self.predict(dummy, conf=0.5)

    def get_model_info(self) -> dict[str, Any]:
        return {
            "model_path": str(self.model_path),
            "num_classes": self.num_classes,
            "class_names": self.class_names,
            "architecture": self.model.__class__.__name__,
        }

    def _to_pil_image(self, image: Any) -> Image.Image:
        if isinstance(image, bytes):
            return Image.open(BytesIO(image)).convert("RGB")
        if isinstance(image, np.ndarray):
            if image.ndim == 2:
                return Image.fromarray(image).convert("RGB")
            return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        if isinstance(image, (str, Path)):
            return Image.open(image).convert("RGB")
        if isinstance(image, Image.Image):
            return image.convert("RGB")
        msg = f"不支持的图像类型: {type(image)}"
        raise RuntimeError(msg)
