"""Stub 推理引擎测试"""

import pytest

from vision_analysis_pro.core.inference.stub_engine import StubInferenceEngine


class TestStubInferenceEngine:
    """Stub 推理引擎测试"""

    def test_normal_mode_returns_detections(self):
        """测试正常模式返回固定检测结果"""
        engine = StubInferenceEngine(mode="normal")
        result = engine.predict(image=b"fake_image_bytes")

        # 应返回 3 个检测结果
        assert len(result) == 3
        assert all(isinstance(item, dict) for item in result)

        # 验证第一个结果的结构
        first = result[0]
        assert "label" in first
        assert "confidence" in first
        assert "bbox" in first
        assert first["label"] == "crack"
        assert first["confidence"] == 0.95
        assert first["bbox"] == [100.0, 150.0, 300.0, 400.0]

    def test_empty_mode_returns_no_detections(self):
        """测试空结果模式"""
        engine = StubInferenceEngine(mode="empty")
        result = engine.predict(image=b"fake_image_bytes")

        assert result == []
        assert len(result) == 0

    def test_confidence_threshold_filtering(self):
        """测试置信度阈值过滤"""
        engine = StubInferenceEngine(mode="normal")

        # conf=0.8 应过滤掉 confidence < 0.8 的结果
        result = engine.predict(image=b"fake_image_bytes", conf=0.8)
        assert len(result) == 2  # crack(0.95) 和 rust(0.88)

        # conf=0.9 应只保留 crack(0.95)
        result = engine.predict(image=b"fake_image_bytes", conf=0.9)
        assert len(result) == 1
        assert result[0]["label"] == "crack"

        # conf=1.0 应返回空
        result = engine.predict(image=b"fake_image_bytes", conf=1.0)
        assert len(result) == 0

    def test_error_mode_raises_exception(self):
        """测试错误模式抛出异常"""
        engine = StubInferenceEngine(mode="error")
        with pytest.raises(RuntimeError, match="模拟：推理失败"):
            engine.predict(image=b"fake_image_bytes")

    def test_warmup_no_op(self):
        """测试预热方法（无操作）"""
        engine = StubInferenceEngine(mode="normal")
        # 不应抛出异常
        engine.warmup()
        engine.warmup(imgsz=1280)

    def test_model_path_optional(self):
        """测试模型路径可选"""
        # 不提供路径应使用默认值
        engine = StubInferenceEngine()
        assert engine.model_path.name == "stub.pt"

        # 提供路径应使用提供的值
        engine = StubInferenceEngine(model_path="models/test.pt")
        assert engine.model_path.name == "test.pt"
