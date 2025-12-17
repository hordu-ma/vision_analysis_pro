"""YOLOv8 推理引擎测试

测试 YOLOInferenceEngine 的功能、边界条件和参数校验。
"""

from pathlib import Path

import numpy as np
import pytest

from vision_analysis_pro.core.inference import YOLOInferenceEngine


class TestYOLOInferenceEngine:
    """YOLOInferenceEngine 功能测试"""

    def test_engine_initialization_success(self) -> None:
        """测试引擎初始化成功"""
        model_path = Path("runs/train/exp/weights/best.pt")
        if not model_path.exists():
            pytest.skip("best.pt 不存在，跳过初始化测试")

        engine = YOLOInferenceEngine(model_path)
        assert engine is not None
        assert engine.model_path == model_path
        assert engine.num_classes > 0
        assert engine.class_names is not None

    def test_engine_initialization_model_not_found(self) -> None:
        """测试模型文件不存在的错误处理"""
        model_path = Path("nonexistent/model.pt")
        with pytest.raises(FileNotFoundError):
            YOLOInferenceEngine(model_path)

    def test_model_info(self) -> None:
        """测试获取模型信息"""
        model_path = Path("runs/train/exp/weights/best.pt")
        if not model_path.exists():
            pytest.skip("best.pt 不存在，跳过测试")

        engine = YOLOInferenceEngine(model_path)
        info = engine.get_model_info()

        assert "model_path" in info
        assert "num_classes" in info
        assert "class_names" in info
        assert info["num_classes"] > 0

    def test_predict_with_dummy_image(self) -> None:
        """测试推理（使用虚拟图像）"""
        model_path = Path("runs/train/exp/weights/best.pt")
        if not model_path.exists():
            pytest.skip("best.pt 不存在，跳过推理测试")

        engine = YOLOInferenceEngine(model_path)

        # 创建虚拟图像（640x640x3）
        dummy_image = np.random.randint(0, 256, (640, 640, 3), dtype=np.uint8)

        # 执行推理
        results = engine.predict(dummy_image, conf=0.5)

        # 验证返回结果格式
        assert isinstance(results, list)
        for detection in results:
            assert "label" in detection
            assert "confidence" in detection
            assert "bbox" in detection

            # 验证字段类型
            assert isinstance(detection["label"], str)
            assert isinstance(detection["confidence"], float)
            assert isinstance(detection["bbox"], list)
            assert len(detection["bbox"]) == 4

            # 验证置信度范围
            assert 0.0 <= detection["confidence"] <= 1.0

            # 验证 bbox 坐标范围（像素坐标）
            bbox = detection["bbox"]
            assert all(coord >= 0 for coord in bbox), f"坐标应为非负: {bbox}"

    def test_predict_confidence_threshold_validation(self) -> None:
        """测试置信度阈值参数校验"""
        model_path = Path("runs/train/exp/weights/best.pt")
        if not model_path.exists():
            pytest.skip("best.pt 不存在，跳过参数校验测试")

        engine = YOLOInferenceEngine(model_path)
        dummy_image = np.random.randint(0, 256, (640, 640, 3), dtype=np.uint8)

        # 无效的置信度（超出范围）
        with pytest.raises(ValueError):
            engine.predict(dummy_image, conf=-0.1)

        with pytest.raises(ValueError):
            engine.predict(dummy_image, conf=1.5)

        # 有效的置信度边界值
        results = engine.predict(dummy_image, conf=0.0)
        assert isinstance(results, list)

        results = engine.predict(dummy_image, conf=1.0)
        assert isinstance(results, list)

    def test_predict_iou_threshold_validation(self) -> None:
        """测试 IoU 阈值参数校验"""
        model_path = Path("runs/train/exp/weights/best.pt")
        if not model_path.exists():
            pytest.skip("best.pt 不存在，跳过参数校验测试")

        engine = YOLOInferenceEngine(model_path)
        dummy_image = np.random.randint(0, 256, (640, 640, 3), dtype=np.uint8)

        # 无效的 IoU（超出范围）
        with pytest.raises(ValueError):
            engine.predict(dummy_image, iou=-0.1)

        with pytest.raises(ValueError):
            engine.predict(dummy_image, iou=1.5)

        # 有效的 IoU 边界值
        results = engine.predict(dummy_image, iou=0.0)
        assert isinstance(results, list)

        results = engine.predict(dummy_image, iou=1.0)
        assert isinstance(results, list)

    def test_warmup(self) -> None:
        """测试模型预热"""
        model_path = Path("runs/train/exp/weights/best.pt")
        if not model_path.exists():
            pytest.skip("best.pt 不存在，跳过预热测试")

        engine = YOLOInferenceEngine(model_path)

        # 预热应不抛出异常
        try:
            engine.warmup(imgsz=640)
        except Exception as e:
            pytest.fail(f"预热失败: {e}")

        # 预热后推理应正常工作
        dummy_image = np.random.randint(0, 256, (640, 640, 3), dtype=np.uint8)
        results = engine.predict(dummy_image, conf=0.5)
        assert isinstance(results, list)

    def test_predict_different_confidence_thresholds(self) -> None:
        """测试不同置信度阈值的过滤效果"""
        model_path = Path("runs/train/exp/weights/best.pt")
        if not model_path.exists():
            pytest.skip("best.pt 不存在，跳过阈值测试")

        engine = YOLOInferenceEngine(model_path)
        dummy_image = np.random.randint(0, 256, (640, 640, 3), dtype=np.uint8)

        # 使用较低阈值（应返回更多结果）
        results_low = engine.predict(dummy_image, conf=0.1)
        num_low = len(results_low)

        # 使用较高阈值（应返回较少结果）
        results_high = engine.predict(dummy_image, conf=0.9)
        num_high = len(results_high)

        # 高阈值应返回不超过低阈值的结果数
        assert num_high <= num_low

    def test_detection_box_format_consistency(self) -> None:
        """测试检测框格式一致性

        所有检测框应包含必需字段，格式与 stub 引擎一致。
        """
        model_path = Path("runs/train/exp/weights/best.pt")
        if not model_path.exists():
            pytest.skip("best.pt 不存在，跳过格式一致性测试")

        engine = YOLOInferenceEngine(model_path)
        dummy_image = np.random.randint(0, 256, (640, 640, 3), dtype=np.uint8)

        results = engine.predict(dummy_image, conf=0.3)

        # 检查每个检测框的字段
        for detection in results:
            # 必需字段
            assert "label" in detection
            assert "confidence" in detection
            assert "bbox" in detection

            # 字段类型
            assert isinstance(detection["label"], str)
            assert isinstance(detection["confidence"], (int, float))
            assert isinstance(detection["bbox"], list)

            # bbox 应为 4 个坐标
            assert len(detection["bbox"]) == 4

            # 坐标应为数字
            for coord in detection["bbox"]:
                assert isinstance(coord, (int, float, np.number))
