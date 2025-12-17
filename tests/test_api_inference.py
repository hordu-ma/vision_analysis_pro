"""API 层测试"""

from typing import Any, Callable

import pytest
from httpx import ASGITransport, AsyncClient

from vision_analysis_pro.settings import Settings, get_settings
from vision_analysis_pro.web.api.deps import get_inference_engine
from vision_analysis_pro.web.api.main import app


class _StubEngine:
    def predict(self, image: Any, conf: float = 0.5, iou: float = 0.5) -> list[dict]:
        return [
            {"label": "crack", "confidence": 0.9, "box": (0.0, 0.0, 1.0, 1.0)},
        ]


@pytest.fixture(autouse=True)
def override_dependencies() -> Callable[[], None]:
    """在测试期间覆盖依赖"""
    original_overrides = app.dependency_overrides.copy()

    def _fake_settings() -> Settings:
        return Settings(
            model_path="models/fake.pt",
            confidence_threshold=0.5,
            iou_threshold=0.5,
        )

    app.dependency_overrides[get_settings] = _fake_settings
    app.dependency_overrides[get_inference_engine] = lambda: _StubEngine()

    yield
    app.dependency_overrides = original_overrides


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "model_loaded" in data


@pytest.mark.asyncio
async def test_inference_endpoint_returns_stub_detection() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/image",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test.jpg"
        assert data["detections"]
        detection = data["detections"][0]
        assert detection["label"] == "crack"
        assert detection["confidence"] > 0
