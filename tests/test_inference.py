"""推理引擎测试"""

import numpy as np
import pytest

from vision_analysis_pro.core.inference.stub_engine import StubInferenceEngine


@pytest.mark.unit
def test_stub_inference_engine_exposes_compatible_interface() -> None:
    """测试 Stub 推理引擎暴露与真实引擎兼容的接口"""
    engine = StubInferenceEngine(mode="normal")

    assert hasattr(engine, "predict")
    assert hasattr(engine, "warmup")
    assert hasattr(engine, "model_path")


@pytest.mark.unit
def test_stub_inference_engine_returns_expected_detections() -> None:
    """测试 Stub 推理引擎返回预期检测结果"""
    engine = StubInferenceEngine(mode="normal")
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    results = engine.predict(image)

    assert len(results) == 3
    assert results[0]["label"] == "crack"
    assert results[0]["confidence"] == 0.95
    assert results[0]["bbox"] == [100.0, 150.0, 300.0, 400.0]


@pytest.mark.unit
def test_stub_inference_engine_empty_mode_returns_no_detections() -> None:
    """测试 Stub 推理引擎空结果模式"""
    engine = StubInferenceEngine(mode="empty")
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    results = engine.predict(image)

    assert results == []


@pytest.mark.unit
def test_stub_inference_engine_error_mode_raises_runtime_error() -> None:
    """测试 Stub 推理引擎错误模式"""
    engine = StubInferenceEngine(mode="error")
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    with pytest.raises(RuntimeError, match="模拟：推理失败"):
        engine.predict(image)
