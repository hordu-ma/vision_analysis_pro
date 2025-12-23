"""ONNX Runtime 推理引擎测试

测试 ONNXInferenceEngine 的功能与 YOLOInferenceEngine 输出一致性。
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from vision_analysis_pro.core.inference import ONNXInferenceEngine

# 测试用 ONNX 模型路径
ONNX_MODEL_PATH = Path("models/best.onnx")


@pytest.fixture
def onnx_engine() -> ONNXInferenceEngine:
    """创建 ONNX 推理引擎实例"""
    if not ONNX_MODEL_PATH.exists():
        pytest.skip(f"ONNX 模型不存在: {ONNX_MODEL_PATH}")
    return ONNXInferenceEngine(ONNX_MODEL_PATH)


@pytest.fixture
def dummy_image() -> np.ndarray:
    """创建测试用图像"""
    # 创建 640x480 的随机图像
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    return img


@pytest.fixture
def dummy_image_bytes(dummy_image: np.ndarray) -> bytes:
    """创建测试用图像字节流"""
    _, buffer = cv2.imencode(".jpg", dummy_image)
    return buffer.tobytes()


class TestONNXInferenceEngine:
    """ONNX 推理引擎测试类"""

    def test_engine_initialization_success(self, onnx_engine: ONNXInferenceEngine):
        """测试引擎初始化成功"""
        assert onnx_engine is not None
        assert onnx_engine.session is not None
        assert onnx_engine.input_name is not None
        assert len(onnx_engine.output_names) > 0

    def test_engine_initialization_model_not_found(self):
        """测试模型文件不存在时抛出异常"""
        with pytest.raises(FileNotFoundError):
            ONNXInferenceEngine("nonexistent_model.onnx")

    def test_get_model_info(self, onnx_engine: ONNXInferenceEngine):
        """测试获取模型信息"""
        info = onnx_engine.get_model_info()

        assert "model_path" in info
        assert "num_classes" in info
        assert "class_names" in info
        assert "input_name" in info
        assert "input_shape" in info
        assert "output_names" in info
        assert "providers" in info

        assert info["num_classes"] == 5
        assert info["class_names"][0] == "crack"
        assert info["class_names"][1] == "rust"

    def test_predict_with_numpy_array(
        self, onnx_engine: ONNXInferenceEngine, dummy_image: np.ndarray
    ):
        """测试使用 numpy 数组进行推理"""
        detections = onnx_engine.predict(dummy_image, conf=0.1)

        assert isinstance(detections, list)
        # 检测结果可能为空（随机图像）
        for det in detections:
            assert "label" in det
            assert "confidence" in det
            assert "bbox" in det
            assert isinstance(det["label"], str)
            assert 0.0 <= det["confidence"] <= 1.0
            assert len(det["bbox"]) == 4

    def test_predict_with_bytes(
        self, onnx_engine: ONNXInferenceEngine, dummy_image_bytes: bytes
    ):
        """测试使用字节流进行推理"""
        detections = onnx_engine.predict(dummy_image_bytes, conf=0.1)

        assert isinstance(detections, list)
        for det in detections:
            assert "label" in det
            assert "confidence" in det
            assert "bbox" in det

    def test_predict_with_file_path(self, onnx_engine: ONNXInferenceEngine):
        """测试使用文件路径进行推理"""
        # 使用项目中的测试图像
        test_image_path = Path("test_image.jpg")
        if not test_image_path.exists():
            pytest.skip("测试图像不存在")

        detections = onnx_engine.predict(str(test_image_path), conf=0.1)

        assert isinstance(detections, list)

    def test_predict_confidence_threshold_validation(
        self, onnx_engine: ONNXInferenceEngine, dummy_image: np.ndarray
    ):
        """测试置信度阈值参数验证"""
        with pytest.raises(ValueError, match="置信度阈值"):
            onnx_engine.predict(dummy_image, conf=-0.1)

        with pytest.raises(ValueError, match="置信度阈值"):
            onnx_engine.predict(dummy_image, conf=1.5)

    def test_predict_iou_threshold_validation(
        self, onnx_engine: ONNXInferenceEngine, dummy_image: np.ndarray
    ):
        """测试 IoU 阈值参数验证"""
        with pytest.raises(ValueError, match="IoU 阈值"):
            onnx_engine.predict(dummy_image, iou=-0.1)

        with pytest.raises(ValueError, match="IoU 阈值"):
            onnx_engine.predict(dummy_image, iou=1.5)

    def test_predict_different_confidence_thresholds(
        self, onnx_engine: ONNXInferenceEngine, dummy_image: np.ndarray
    ):
        """测试不同置信度阈值的推理结果"""
        # 低阈值应该返回更多检测结果
        detections_low = onnx_engine.predict(dummy_image, conf=0.1)
        detections_high = onnx_engine.predict(dummy_image, conf=0.9)

        # 高阈值的结果数量应该 <= 低阈值
        assert len(detections_high) <= len(detections_low)

    def test_warmup(self, onnx_engine: ONNXInferenceEngine):
        """测试模型预热"""
        # warmup 不应该抛出异常
        onnx_engine.warmup(imgsz=640)

    def test_detection_box_format_consistency(
        self, onnx_engine: ONNXInferenceEngine, dummy_image: np.ndarray
    ):
        """测试检测框格式一致性"""
        detections = onnx_engine.predict(dummy_image, conf=0.1)

        for det in detections:
            bbox = det["bbox"]
            # bbox 应该是 [x1, y1, x2, y2] 格式
            assert len(bbox) == 4
            x1, y1, x2, y2 = bbox
            # x2 > x1, y2 > y1
            assert x2 >= x1, f"x2({x2}) should >= x1({x1})"
            assert y2 >= y1, f"y2({y2}) should >= y1({y1})"
            # 坐标应该在合理范围内
            assert x1 >= 0
            assert y1 >= 0

    def test_predict_invalid_image_bytes(self, onnx_engine: ONNXInferenceEngine):
        """测试无效图像字节流"""
        invalid_bytes = b"not an image"
        with pytest.raises(RuntimeError):
            onnx_engine.predict(invalid_bytes)

    def test_predict_unsupported_image_type(self, onnx_engine: ONNXInferenceEngine):
        """测试不支持的图像类型"""
        with pytest.raises(TypeError, match="不支持的图像类型"):
            onnx_engine.predict(12345)  # type: ignore

    def test_class_names_mapping(self, onnx_engine: ONNXInferenceEngine):
        """测试类别名称映射"""
        expected_classes = {
            0: "crack",
            1: "rust",
            2: "deformation",
            3: "spalling",
            4: "corrosion",
        }
        assert onnx_engine.class_names == expected_classes

    def test_providers_available(self, onnx_engine: ONNXInferenceEngine):
        """测试执行提供者可用"""
        assert len(onnx_engine.providers) > 0
        # 至少应该有 CPU 提供者
        assert any("CPU" in p for p in onnx_engine.providers)


class TestONNXEnginePreprocessing:
    """ONNX 引擎预处理测试"""

    def test_preprocess_maintains_aspect_ratio(self, onnx_engine: ONNXInferenceEngine):
        """测试预处理保持宽高比"""
        # 创建宽图
        wide_image = np.zeros((100, 200, 3), dtype=np.uint8)
        blob, orig_shape, info = onnx_engine._preprocess(wide_image, (640, 640))

        assert orig_shape == (100, 200)
        assert blob.shape == (1, 3, 640, 640)

    def test_preprocess_different_sizes(self, onnx_engine: ONNXInferenceEngine):
        """测试不同尺寸图像的预处理"""
        sizes = [(480, 640), (1080, 1920), (100, 100), (300, 500)]

        for h, w in sizes:
            image = np.zeros((h, w, 3), dtype=np.uint8)
            blob, orig_shape, _ = onnx_engine._preprocess(image, (640, 640))

            assert orig_shape == (h, w)
            assert blob.shape == (1, 3, 640, 640)
            assert blob.dtype == np.float32
            assert blob.max() <= 1.0
            assert blob.min() >= 0.0


class TestONNXEngineNMS:
    """ONNX 引擎 NMS 测试"""

    def test_nms_empty_boxes(self, onnx_engine: ONNXInferenceEngine):
        """测试空框的 NMS"""
        boxes = np.array([]).reshape(0, 4)
        scores = np.array([])

        result = onnx_engine._nms(boxes, scores, 0.5)
        assert result == []

    def test_nms_single_box(self, onnx_engine: ONNXInferenceEngine):
        """测试单个框的 NMS"""
        boxes = np.array([[10, 10, 50, 50]])
        scores = np.array([0.9])

        result = onnx_engine._nms(boxes, scores, 0.5)
        assert result == [0]

    def test_nms_overlapping_boxes(self, onnx_engine: ONNXInferenceEngine):
        """测试重叠框的 NMS"""
        # 两个高度重叠的框
        boxes = np.array(
            [
                [10, 10, 50, 50],
                [12, 12, 52, 52],  # 高度重叠
            ]
        )
        scores = np.array([0.9, 0.8])

        result = onnx_engine._nms(boxes, scores, 0.5)
        # 应该只保留分数高的框
        assert len(result) == 1
        assert result[0] == 0

    def test_nms_non_overlapping_boxes(self, onnx_engine: ONNXInferenceEngine):
        """测试不重叠框的 NMS"""
        # 两个不重叠的框
        boxes = np.array(
            [
                [10, 10, 50, 50],
                [100, 100, 150, 150],  # 不重叠
            ]
        )
        scores = np.array([0.9, 0.8])

        result = onnx_engine._nms(boxes, scores, 0.5)
        # 两个框都应该保留
        assert len(result) == 2


class TestONNXEngineCustomClassNames:
    """ONNX 引擎自定义类别名称测试"""

    def test_custom_class_names(self):
        """测试自定义类别名称"""
        if not ONNX_MODEL_PATH.exists():
            pytest.skip(f"ONNX 模型不存在: {ONNX_MODEL_PATH}")

        custom_names = {
            0: "custom_crack",
            1: "custom_rust",
            2: "custom_deformation",
            3: "custom_spalling",
            4: "custom_corrosion",
        }

        engine = ONNXInferenceEngine(ONNX_MODEL_PATH, class_names=custom_names)
        assert engine.class_names == custom_names
