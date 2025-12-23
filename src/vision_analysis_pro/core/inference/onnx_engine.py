"""ONNX Runtime 推理引擎

使用 ONNX Runtime 进行高性能跨平台推理，支持 CPU/GPU 加速。
输出格式与 YOLOInferenceEngine 保持一致。
"""

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .base import InferenceEngine


class ONNXInferenceEngine(InferenceEngine):
    """基于 ONNX Runtime 的推理引擎

    将 ONNX 模型输出解析并转换为标准 DetectionBox 格式：
    - label: 类别名称 (str)
    - confidence: 置信度 (float, [0.0, 1.0])
    - bbox: [x1, y1, x2, y2] 像素坐标 (list[float])

    支持特性：
    - CPU/GPU 自动选择
    - 动态/静态输入尺寸
    - 与 YOLO 引擎输出格式一致
    """

    # 默认类别名称（与训练数据集一致）
    DEFAULT_CLASS_NAMES: dict[int, str] = {
        0: "crack",
        1: "rust",
        2: "deformation",
        3: "spalling",
        4: "corrosion",
    }

    def __init__(
        self,
        model_path: str | Path,
        providers: list[str] | None = None,
        class_names: dict[int, str] | None = None,
    ) -> None:
        """初始化 ONNX Runtime 推理引擎

        Args:
            model_path: ONNX 模型文件路径（.onnx 格式）
            providers: 执行提供者列表，默认自动选择
                       例如: ["CUDAExecutionProvider", "CPUExecutionProvider"]
            class_names: 类别 ID 到名称的映射，默认使用内置定义

        Raises:
            FileNotFoundError: 模型文件不存在
            ImportError: onnxruntime 未安装
            RuntimeError: 模型加载失败
        """
        super().__init__(model_path)

        # 延迟导入，避免未安装时报错
        try:
            import onnxruntime as ort
        except ImportError as e:
            msg = "需要安装 onnxruntime: uv sync --extra onnx"
            raise ImportError(msg) from e

        # 设置执行提供者
        if providers is None:
            # 自动选择可用的执行提供者
            available = ort.get_available_providers()
            if "CUDAExecutionProvider" in available:
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            elif "CoreMLExecutionProvider" in available:
                providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
            else:
                providers = ["CPUExecutionProvider"]

        # 创建推理会话
        try:
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )

            self.session = ort.InferenceSession(
                str(self.model_path),
                sess_options=sess_options,
                providers=providers,
            )
        except Exception as e:
            msg = f"ONNX 模型加载失败: {e}"
            raise RuntimeError(msg) from e

        # 获取输入输出信息
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        self.output_names = [out.name for out in self.session.get_outputs()]

        # 类别名称
        self.class_names = class_names or self.DEFAULT_CLASS_NAMES
        self.num_classes = len(self.class_names)

        # 记录使用的执行提供者
        self.providers = self.session.get_providers()

    def _preprocess(
        self, image: np.ndarray, target_size: tuple[int, int] = (640, 640)
    ) -> tuple[np.ndarray, tuple[int, int], tuple[float, float]]:
        """预处理图像

        Args:
            image: 输入图像 (HxWxC, BGR)
            target_size: 目标尺寸 (height, width)

        Returns:
            (预处理后的图像, 原始尺寸, 缩放比例)
        """
        orig_h, orig_w = image.shape[:2]
        target_h, target_w = target_size

        # 计算缩放比例（保持宽高比）
        scale = min(target_w / orig_w, target_h / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)

        # 缩放图像
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # 创建目标尺寸的画布（填充灰色）
        canvas = np.full((target_h, target_w, 3), 114, dtype=np.uint8)

        # 将缩放后的图像放到画布中心
        pad_w = (target_w - new_w) // 2
        pad_h = (target_h - new_h) // 2
        canvas[pad_h : pad_h + new_h, pad_w : pad_w + new_w] = resized

        # BGR -> RGB
        canvas = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)

        # HWC -> CHW, 归一化到 [0, 1]
        blob = canvas.transpose(2, 0, 1).astype(np.float32) / 255.0

        # 添加 batch 维度
        blob = np.expand_dims(blob, axis=0)

        return blob, (orig_h, orig_w), (scale, pad_w, pad_h)

    def _postprocess(
        self,
        outputs: np.ndarray,
        orig_shape: tuple[int, int],
        preprocess_info: tuple[float, float, float],
        conf_threshold: float,
        iou_threshold: float,
    ) -> list[dict[str, Any]]:
        """后处理推理输出

        Args:
            outputs: 模型原始输出 (1, num_classes+4, num_anchors)
            orig_shape: 原始图像尺寸 (height, width)
            preprocess_info: 预处理信息 (scale, pad_w, pad_h)
            conf_threshold: 置信度阈值
            iou_threshold: NMS IoU 阈值

        Returns:
            检测结果列表
        """
        orig_h, orig_w = orig_shape
        scale, pad_w, pad_h = preprocess_info

        # YOLO 输出格式: (1, 4+num_classes, num_anchors)
        # 转置为 (num_anchors, 4+num_classes)
        predictions = outputs[0].transpose(1, 0)

        # 提取 bbox 和类别分数
        # 前 4 列是 cx, cy, w, h
        boxes = predictions[:, :4]
        scores = predictions[:, 4:]

        # 获取每个框的最大类别分数和类别 ID
        max_scores = np.max(scores, axis=1)
        class_ids = np.argmax(scores, axis=1)

        # 置信度过滤
        mask = max_scores > conf_threshold
        boxes = boxes[mask]
        max_scores = max_scores[mask]
        class_ids = class_ids[mask]

        if len(boxes) == 0:
            return []

        # 转换 cx, cy, w, h -> x1, y1, x2, y2
        x1 = boxes[:, 0] - boxes[:, 2] / 2
        y1 = boxes[:, 1] - boxes[:, 3] / 2
        x2 = boxes[:, 0] + boxes[:, 2] / 2
        y2 = boxes[:, 1] + boxes[:, 3] / 2

        # 还原到原始图像坐标
        x1 = (x1 - pad_w) / scale
        y1 = (y1 - pad_h) / scale
        x2 = (x2 - pad_w) / scale
        y2 = (y2 - pad_h) / scale

        # 裁剪到图像边界
        x1 = np.clip(x1, 0, orig_w)
        y1 = np.clip(y1, 0, orig_h)
        x2 = np.clip(x2, 0, orig_w)
        y2 = np.clip(y2, 0, orig_h)

        # 组合 bbox
        bboxes = np.stack([x1, y1, x2, y2], axis=1)

        # NMS
        indices = self._nms(bboxes, max_scores, iou_threshold)

        # 构建检测结果
        detections: list[dict[str, Any]] = []
        for idx in indices:
            cls_id = int(class_ids[idx])
            class_name = self.class_names.get(cls_id, f"class_{cls_id}")

            detection = {
                "label": class_name,
                "confidence": float(max_scores[idx]),
                "bbox": [float(x) for x in bboxes[idx]],
            }
            detections.append(detection)

        return detections

    def _nms(
        self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float
    ) -> list[int]:
        """非极大值抑制 (NMS)

        Args:
            boxes: 边界框 (N, 4) [x1, y1, x2, y2]
            scores: 置信度分数 (N,)
            iou_threshold: IoU 阈值

        Returns:
            保留的框索引列表
        """
        if len(boxes) == 0:
            return []

        # 按分数降序排列
        order = scores.argsort()[::-1]

        keep = []
        while len(order) > 0:
            i = order[0]
            keep.append(i)

            if len(order) == 1:
                break

            # 计算当前框与其他框的 IoU
            xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
            yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
            xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
            yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])

            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            intersection = w * h

            area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
            area_others = (boxes[order[1:], 2] - boxes[order[1:], 0]) * (
                boxes[order[1:], 3] - boxes[order[1:], 1]
            )
            union = area_i + area_others - intersection

            iou = intersection / (union + 1e-6)

            # 保留 IoU 小于阈值的框
            mask = iou <= iou_threshold
            order = order[1:][mask]

        return keep

    def predict(
        self, image: Any, conf: float = 0.5, iou: float = 0.5
    ) -> list[dict[str, Any]]:
        """执行推理

        Args:
            image: 输入图像（支持多种格式）:
                - numpy 数组 (HxWxC, BGR)
                - 文件路径 (str/Path)
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

        # 加载图像
        if isinstance(image, bytes):
            try:
                nparr = np.frombuffer(image, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if image is None:
                    msg = "无法解码图像字节流（可能不是有效的图像格式）"
                    raise RuntimeError(msg)
            except RuntimeError:
                raise
            except Exception as e:
                msg = f"图像解码失败: {e}"
                raise RuntimeError(msg) from e
        elif isinstance(image, (str, Path)):
            image = cv2.imread(str(image))
            if image is None:
                msg = f"无法读取图像文件: {image}"
                raise RuntimeError(msg)
        elif not isinstance(image, np.ndarray):
            msg = f"不支持的图像类型: {type(image)}"
            raise TypeError(msg)

        # 获取目标尺寸
        if len(self.input_shape) == 4:
            target_h = (
                self.input_shape[2] if isinstance(self.input_shape[2], int) else 640
            )
            target_w = (
                self.input_shape[3] if isinstance(self.input_shape[3], int) else 640
            )
        else:
            target_h, target_w = 640, 640

        try:
            # 预处理
            blob, orig_shape, preprocess_info = self._preprocess(
                image, (target_h, target_w)
            )

            # 推理
            outputs = self.session.run(self.output_names, {self.input_name: blob})

            # 后处理
            detections = self._postprocess(
                outputs[0],
                orig_shape,
                preprocess_info,
                conf,
                iou,
            )

            return detections

        except Exception as e:
            msg = f"推理失败: {e}"
            raise RuntimeError(msg) from e

    def warmup(self, imgsz: int = 640) -> None:
        """预热模型

        在首次推理前执行，初始化 ONNX Runtime 会话。

        Args:
            imgsz: 输入图像尺寸
        """
        try:
            # 创建随机输入进行预热
            dummy_input = np.random.rand(1, 3, imgsz, imgsz).astype(np.float32)
            self.session.run(self.output_names, {self.input_name: dummy_input})
        except Exception:
            # 预热失败不影响后续使用
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
            "input_name": self.input_name,
            "input_shape": self.input_shape,
            "output_names": self.output_names,
            "providers": self.providers,
        }
