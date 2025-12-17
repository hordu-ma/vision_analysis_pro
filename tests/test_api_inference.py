"""API 层测试"""

import pytest
from httpx import ASGITransport, AsyncClient

from vision_analysis_pro.core.inference.stub_engine import StubInferenceEngine
from vision_analysis_pro.settings import Settings, get_settings
from vision_analysis_pro.web.api.deps import get_inference_engine
from vision_analysis_pro.web.api.main import app


@pytest.fixture(autouse=True)
def override_dependencies():
    """在测试期间覆盖依赖（使用 stub 引擎）"""
    original_overrides = app.dependency_overrides.copy()

    def _fake_settings() -> Settings:
        return Settings(
            model_path="models/fake.pt",
            confidence_threshold=0.5,
            iou_threshold=0.5,
        )

    app.dependency_overrides[get_settings] = _fake_settings
    app.dependency_overrides[get_inference_engine] = lambda: StubInferenceEngine(
        mode="normal"
    )

    yield
    app.dependency_overrides = original_overrides


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """测试健康检查接口"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "model_loaded" in data


@pytest.mark.asyncio
async def test_inference_endpoint_returns_detections() -> None:
    """测试推理接口返回检测结果"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/image",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()

        # 验证响应结构
        assert data["filename"] == "test.jpg"
        assert "detections" in data
        assert "metadata" in data

        # 验证检测结果（stub 默认返回 3 个结果）
        detections = data["detections"]
        assert len(detections) == 3
        assert detections[0]["label"] == "crack"
        assert detections[0]["confidence"] == 0.95
        assert detections[0]["bbox"] == [100.0, 150.0, 300.0, 400.0]


@pytest.mark.asyncio
async def test_inference_endpoint_empty_file() -> None:
    """测试上传空文件返回错误"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/image",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "EMPTY_FILE"
        assert "message" in data


@pytest.mark.asyncio
async def test_inference_endpoint_file_too_large() -> None:
    """测试上传超大文件返回错误"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 创建超过 10MB 的文件
        large_file = b"x" * (11 * 1024 * 1024)
        resp = await client.post(
            "/api/v1/inference/image",
            files={"file": ("large.jpg", large_file, "image/jpeg")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "FILE_TOO_LARGE"
        assert "message" in data


@pytest.mark.asyncio
async def test_inference_endpoint_invalid_format() -> None:
    """测试上传非图片格式返回错误"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/image",
            files={"file": ("document.pdf", b"fake-pdf-content", "application/pdf")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "INVALID_FORMAT"
        assert "message" in data


@pytest.mark.asyncio
async def test_inference_endpoint_error_mode() -> None:
    """测试推理引擎错误时返回 500"""
    # 临时覆盖为 error 模式引擎
    app.dependency_overrides[get_inference_engine] = lambda: StubInferenceEngine(
        mode="error"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/image",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )
        assert resp.status_code == 500
        data = resp.json()
        assert data["code"] == "INFERENCE_ERROR"
        assert "message" in data
