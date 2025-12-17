"""边界条件与异常路径测试

补齐各种边界情况和错误处理路径的测试覆盖。
"""

from pathlib import Path

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from vision_analysis_pro.core.inference import YOLOInferenceEngine
from vision_analysis_pro.core.inference.stub_engine import StubInferenceEngine
from vision_analysis_pro.settings import Settings, get_settings
from vision_analysis_pro.web.api.deps import get_inference_engine
from vision_analysis_pro.web.api.main import app


def _create_test_image(width: int = 100, height: int = 100) -> bytes:
    """创建测试图像

    Args:
        width: 图像宽度
        height: 图像高度

    Returns:
        JPEG 编码的图像字节
    """
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (128, 128, 128)
    success, encoded = cv2.imencode(".jpg", img)
    assert success
    return encoded.tobytes()


class TestAPIWithYOLOEngine:
    """测试 API 在使用 YOLO 引擎时的集成场景"""

    @pytest.fixture(autouse=True)
    def setup_yolo_engine(self):
        """设置 YOLO 引擎依赖"""
        model_path = Path("runs/train/exp/weights/best.pt")
        if not model_path.exists():
            pytest.skip("best.pt 不存在，跳过 YOLO 引擎集成测试")

        original_overrides = app.dependency_overrides.copy()

        def _fake_settings() -> Settings:
            return Settings(
                model_path=str(model_path),
                confidence_threshold=0.3,
                iou_threshold=0.5,
            )

        def _get_yolo_engine() -> YOLOInferenceEngine:
            return YOLOInferenceEngine(model_path)

        app.dependency_overrides[get_settings] = _fake_settings
        app.dependency_overrides[get_inference_engine] = _get_yolo_engine

        yield

        app.dependency_overrides = original_overrides

    @pytest.mark.asyncio
    async def test_inference_with_yolo_engine(self) -> None:
        """测试使用 YOLO 引擎进行推理"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            image_bytes = _create_test_image()
            files = {"file": ("test.jpg", image_bytes, "image/jpeg")}

            response = await client.post("/api/v1/inference/image", files=files)

            assert response.status_code == 200
            data = response.json()

            # 验证响应结构
            assert "filename" in data
            assert "detections" in data
            assert "metadata" in data
            assert isinstance(data["detections"], list)

            # 验证每个检测结果
            for detection in data["detections"]:
                assert "label" in detection
                assert "confidence" in detection
                assert "bbox" in detection
                assert len(detection["bbox"]) == 4

    @pytest.mark.asyncio
    async def test_inference_with_visualization(self) -> None:
        """测试带可视化的推理"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            image_bytes = _create_test_image()
            files = {"file": ("test.jpg", image_bytes, "image/jpeg")}

            response = await client.post(
                "/api/v1/inference/image?visualize=true", files=files
            )

            assert response.status_code == 200
            data = response.json()

            # 如果有检测结果，应包含可视化
            if data["detections"]:
                assert "visualization" in data
                assert data["visualization"] is not None
            else:
                # 即使无检测，也可能返回可视化
                assert "visualization" in data

    @pytest.mark.asyncio
    async def test_corrupted_image_with_yolo(self) -> None:
        """测试 YOLO 引擎处理损坏的图像"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 随机字节（非图像）
            corrupted_data = b"this is not an image" * 100

            files = {"file": ("corrupted.jpg", corrupted_data, "image/jpeg")}
            response = await client.post("/api/v1/inference/image", files=files)

            # YOLO 引擎应该返回错误
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


class TestDependencyInjection:
    """测试依赖注入和引擎切换"""

    def test_get_inference_engine_with_yolo(self, monkeypatch) -> None:
        """测试通过环境变量获取 YOLO 引擎"""
        model_path = Path("runs/train/exp/weights/best.pt")
        if not model_path.exists():
            pytest.skip("best.pt 不存在，跳过测试")

        monkeypatch.setenv("INFERENCE_ENGINE", "yolo")
        monkeypatch.setenv("YOLO_MODEL_PATH", str(model_path))

        # 清除 LRU 缓存
        from vision_analysis_pro.web.api.deps import _load_yolo_engine

        _load_yolo_engine.cache_clear()

        settings = Settings()
        engine = get_inference_engine(settings)

        assert isinstance(engine, YOLOInferenceEngine)

    def test_get_inference_engine_with_stub(self, monkeypatch) -> None:
        """测试通过环境变量获取 Stub 引擎"""
        monkeypatch.setenv("INFERENCE_ENGINE", "stub")

        settings = Settings()
        engine = get_inference_engine(settings)

        assert isinstance(engine, StubInferenceEngine)


class TestEdgeCases:
    """边界条件测试"""

    @pytest.fixture(autouse=True)
    def setup_stub_engine(self):
        """设置 stub 引擎"""
        original_overrides = app.dependency_overrides.copy()

        app.dependency_overrides[get_inference_engine] = lambda: StubInferenceEngine(
            mode="normal"
        )

        yield

        app.dependency_overrides = original_overrides

    @pytest.mark.asyncio
    async def test_very_large_image(self) -> None:
        """测试非常大的图像（接近限制）"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 创建接近 10MB 的图像
            large_image = _create_test_image(width=3000, height=2500)

            files = {"file": ("large.jpg", large_image, "image/jpeg")}
            response = await client.post("/api/v1/inference/image", files=files)

            # 应该成功或返回合理的错误
            assert response.status_code in [200, 400, 413]

    @pytest.mark.asyncio
    async def test_tiny_image(self) -> None:
        """测试极小的图像"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            tiny_image = _create_test_image(width=10, height=10)

            files = {"file": ("tiny.jpg", tiny_image, "image/jpeg")}
            response = await client.post("/api/v1/inference/image", files=files)

            # 应该能处理（stub 引擎不依赖图像内容）
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_corrupted_image_data(self) -> None:
        """测试损坏的图像数据"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 随机字节（非图像）
            corrupted_data = b"this is not an image" * 100

            files = {"file": ("corrupted.jpg", corrupted_data, "image/jpeg")}
            response = await client.post("/api/v1/inference/image", files=files)

            # Stub 引擎不处理图像内容，会返回 200
            # YOLO 引擎会在解码时失败，返回错误
            # 这里测试 stub 引擎场景
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_multiple_files_upload(self) -> None:
        """测试上传多个文件（应只处理第一个）"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            image1 = _create_test_image()
            image2 = _create_test_image()

            files = [
                ("file", ("test1.jpg", image1, "image/jpeg")),
                ("file", ("test2.jpg", image2, "image/jpeg")),
            ]
            response = await client.post("/api/v1/inference/image", files=files)

            # 应该成功处理第一个文件
            assert response.status_code == 200


class TestErrorRecovery:
    """错误恢复测试"""

    @pytest.fixture(autouse=True)
    def setup_error_engine(self):
        """设置会出错的引擎"""
        original_overrides = app.dependency_overrides.copy()

        app.dependency_overrides[get_inference_engine] = lambda: StubInferenceEngine(
            mode="error"
        )

        yield

        app.dependency_overrides = original_overrides

    @pytest.mark.asyncio
    async def test_inference_engine_error_handling(self) -> None:
        """测试推理引擎抛出异常时的错误处理"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            image_bytes = _create_test_image()
            files = {"file": ("test.jpg", image_bytes, "image/jpeg")}

            response = await client.post("/api/v1/inference/image", files=files)

            # 应该返回 500 错误
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


class TestConcurrency:
    """并发测试"""

    @pytest.fixture(autouse=True)
    def setup_stub_engine(self):
        """设置 stub 引擎"""
        original_overrides = app.dependency_overrides.copy()

        app.dependency_overrides[get_inference_engine] = lambda: StubInferenceEngine(
            mode="normal"
        )

        yield

        app.dependency_overrides = original_overrides

    @pytest.mark.asyncio
    async def test_concurrent_requests(self) -> None:
        """测试并发请求处理"""
        import asyncio

        transport = ASGITransport(app=app)

        async def make_request(client: AsyncClient) -> int:
            image_bytes = _create_test_image()
            files = {"file": ("test.jpg", image_bytes, "image/jpeg")}
            response = await client.post("/api/v1/inference/image", files=files)
            return response.status_code

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 并发 5 个请求
            tasks = [make_request(client) for _ in range(5)]
            results = await asyncio.gather(*tasks)

            # 所有请求应该成功
            assert all(status == 200 for status in results)
