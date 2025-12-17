"""YOLOv8 推理引擎

使用 Ultralytics YOLO 进行真实推理，并将结果转换为标准 schema。
"""

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .base import InferenceEngine


class YOLOInferenceEngine(InferenceEngine):
    """基于 Ultralytics YOLOv8 的推理引擎

    将 YOLO 输出解析并转换为标准 DetectionBox 格式：
    - label: 类别名称 (str)
    - confidence: 置信度 (float, [0.0, 1.0])
    - bbox: [x1, y1, x2, y2] 像素坐标 (list[float])
    """

    def __init__(self, model_path: str | Path) -> None:
        """初始化 YOLO 推理引擎

        Args:
            model_path: 模型文件路径（.pt 格式）

        Raises:
            FileNotFoundError: 模型文件不存在
            ImportError: ultralytics 未安装
            RuntimeError: 模型加载失败
        """
        super().__init__(model_path)

        # 延迟导入，避免未安装时报错
        try:
            from ultralytics import YOLO
        except ImportError as e:
            msg = "需要安装 ultralytics: uv pip install ultralytics"
            raise ImportError(msg) from e

        try:
            self.model = YOLO(str(self.model_path))
        except Exception as e:
            msg = f"模型加载失败: {e}"
            raise RuntimeError(msg) from e

        # 模型元信息
        self.num_classes = self.model.model.nc if hasattr(self.model.model, "nc") else 5
        # 类别名称字典
        self.class_names = self.model.names

    def predict(
        self, image: Any, conf: float = 0.5, iou: float = 0.5
    ) -> list[dict[str, Any]]:
        """执行推理

        Args:
            image: 输入图像（支持多种格式）:
                - numpy 数组 (HxWxC)
                - PIL Image
                - 文件路径 (str/Path)
                - URL (http/https)
                - 图像字节流 (bytes)
            conf: 置信度阈值 (0.0 - 1.0)
            iou: NMS IoU 阈值 (0.0 - 1.0)

        Returns:
            检测结果列表，每项包含：
            - label: 类别名称
            - confidence: 置信度
            - bbox: [x1, y1, x2, y2] 像素坐标
        """
        # 参数校验
        if not (0.0 <= conf <= 1.0):
            msg = f"置信度阈值应在 [0.0, 1.0] 范围内，实际: {conf}"
            raise ValueError(msg)
        if not (0.0 <= iou <= 1.0):
            msg = f"IoU 阈值应在 [0.0, 1.0] 范围内，实际: {iou}"
            raise ValueError(msg)

        # 如果是字节流，转换为 numpy 数组
        if isinstance(image, bytes):
            try:
                nparr = np.frombuffer(image, np.uint8)
                decoded_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if decoded_image is None:
                    msg = "无法解码图像字节流（可能不是有效的图像格式）"
                    raise RuntimeError(msg)
                image = decoded_image
            except RuntimeError:
                # 重新抛出 RuntimeError
                raise
            except Exception as e:
                msg = f"图像解码失败: {e}"
                raise RuntimeError(msg) from e

        try:
            # 执行推理
            results = self.model(image, conf=conf, iou=iou, verbose=False)

            # 解析 YOLO 结果
            detections: list[dict[str, Any]] = []
            for result in results:
                if result.boxes is None or len(result.boxes) == 0:
                    continue

                # 获取检测框、置信度、类别 ID
                boxes = result.boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
                confs = result.boxes.conf.cpu().numpy()
                cls_ids = result.boxes.cls.cpu().numpy()

                # 构建检测结果
                for box, conf_val, cls_id in zip(boxes, confs, cls_ids, strict=True):
                    cls_id_int = int(cls_id)
                    class_name = self.class_names.get(cls_id_int, f"class_{cls_id_int}")

                    detection = {
                        "label": class_name,
                        "confidence": float(conf_val),
                        "bbox": [float(x) for x in box],  # [x1, y1, x2, y2]
                    }
                    detections.append(detection)

            return detections

        except Exception as e:
            msg = f"推理失败: {e}"
            raise RuntimeError(msg) from e

    def warmup(self, imgsz: int = 640) -> None:
        """预热模型

        在首次推理前执行，加载模型到设备并初始化计算图。

        Args:
            imgsz: 输入图像尺寸
        """
        try:
            # 某些版本的 ultralytics 支持 warmup 方法
            if hasattr(self.model, "warmup"):
                self.model.warmup(imgsz=imgsz)
        except Exception:
            # 如果 warmup 失败，则忽略（模型仍可用）
            # 许多版本的 YOLO 没有显式的 warmup 方法
            pass

    def get_model_info(self) -> dict[str, Any]:
        """获取模型信息

        Returns:
            包含模型元信息的字典
        """
        return {
            "model_path": str(self.model_path),
            "num_classes": self.num_classes,
            "class_names": self.class_names,
            "device": str(self.model.device)
            if hasattr(self.model, "device")
            else "unknown",
        }
