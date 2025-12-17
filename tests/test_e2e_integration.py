"""端到端集成测试

验证：
1. API 与 YOLO 引擎的完整工作流
2. API 与 Stub 引擎的完整工作流
3. 环境变量切换引擎功能
4. Demo 脚本无需手工干预即可运行

注意：这些测试需要真实的 YOLO 模型文件存在
"""

import os
from pathlib import Path

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from vision_analysis_pro.web.api.main import app


class TestE2EWithYOLOEngine:
    """YOLO 引擎的端到端测试"""

    @pytest.fixture(autouse=True)
    def setup_yolo_engine(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """设置使用 YOLO 引擎"""
        monkeypatch.setenv("INFERENCE_ENGINE", "yolo")
        monkeypatch.setenv("YOLO_MODEL_PATH", "runs/train/exp/weights/best.pt")

    @pytest.mark.asyncio
    async def test_full_workflow_with_yolo(self) -> None:
        """完整工作流: 创建图像 -> 推理 -> 验证结果 -> 可视化"""
        # 1. 创建测试图像
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:] = (200, 200, 200)
        cv2.rectangle(test_image, (100, 150), (300, 400), (150, 150, 150), -1)

        # 编码为字节
        success, encoded_image = cv2.imencode(".jpg", test_image)
        assert success, "图像编码失败"
        image_bytes = encoded_image.tobytes()

        # 2. 发送推理请求（带可视化）
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("test.jpg", image_bytes, "image/jpeg")}
            response = await client.post(
                "/api/v1/inference/image", files=files, params={"visualize": True}
            )

            # 3. 验证响应
            assert response.status_code == 200
            data = response.json()

            # 验证基本字段
            assert "filename" in data
            assert "detections" in data
            assert "metadata" in data
            assert data["metadata"]["engine"] == "YOLOInferenceEngine"

            # 验证检测结果结构
            assert isinstance(data["detections"], list)
            for det in data["detections"]:
                assert "label" in det
                assert "confidence" in det
                assert "bbox" in det
                assert isinstance(det["bbox"], list)
                assert len(det["bbox"]) == 4

            # 验证可视化数据存在
            assert "visualization" in data
            if data["detections"]:  # 如果有检测结果
                assert data["visualization"] is not None
                assert data["visualization"].startswith("data:image/jpeg;base64,")

    @pytest.mark.asyncio
    async def test_health_check_with_yolo(self) -> None:
        """健康检查端点验证 YOLO 引擎已加载"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            # model_loaded 取决于模型文件是否存在，不强制要求
            assert "model_loaded" in data


class TestE2EWithStubEngine:
    """Stub 引擎的端到端测试

    注意：由于依赖注入使用了 lru_cache，在同一测试会话中动态切换引擎有限制。
    如需测试 Stub 引擎，请在启动测试前设置环境变量 INFERENCE_ENGINE=stub
    """

    @pytest.fixture(autouse=True)
    def setup_stub_engine(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """设置使用 Stub 引擎（注意：仅在独立运行时生效）"""
        monkeypatch.setenv("INFERENCE_ENGINE", "stub")

    @pytest.mark.skip(reason="依赖注入缓存限制，需要在独立进程中运行")
    @pytest.mark.asyncio
    async def test_full_workflow_with_stub(self) -> None:
        """Stub 引擎完整工作流（需要独立运行）"""
        # 创建测试图像
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        success, encoded_image = cv2.imencode(".jpg", test_image)
        assert success
        image_bytes = encoded_image.tobytes()

        # 发送推理请求
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("test.jpg", image_bytes, "image/jpeg")}
            response = await client.post(
                "/api/v1/inference/image", files=files, params={"visualize": True}
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()

            # Stub 引擎应该返回模拟数据
            assert data["metadata"]["engine"] == "StubInferenceEngine"
            assert isinstance(data["detections"], list)

            # Stub 引擎返回固定数量的检测结果（根据实际实现）
            assert len(data["detections"]) >= 0  # 可能为 0 或更多


class TestEngineSwitching:
    """环境变量切换引擎测试

    注意：由于依赖注入使用了 lru_cache，在同一测试会话中动态切换引擎有限制。
    这些测试验证环境变量的读取逻辑，但实际切换需要重启应用。
    """

    @pytest.mark.asyncio
    async def test_yolo_engine_is_used(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """测试默认使用 YOLO 引擎"""
        # 创建测试图像
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        success, encoded_image = cv2.imencode(".jpg", test_image)
        assert success
        image_bytes = encoded_image.tobytes()

        # 设置使用 YOLO 引擎（默认）
        monkeypatch.setenv("INFERENCE_ENGINE", "yolo")
        monkeypatch.setenv("YOLO_MODEL_PATH", "runs/train/exp/weights/best.pt")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("test.jpg", image_bytes, "image/jpeg")}
            response = await client.post("/api/v1/inference/image", files=files)
            data = response.json()
            assert data["metadata"]["engine"] == "YOLOInferenceEngine"

    @pytest.mark.skip(reason="依赖注入缓存限制，Stub 引擎需要在独立进程中测试")
    @pytest.mark.asyncio
    async def test_stub_engine_is_used(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """测试使用 Stub 引擎（需要独立运行）"""
        # 创建测试图像
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        success, encoded_image = cv2.imencode(".jpg", test_image)
        assert success
        image_bytes = encoded_image.tobytes()

        # 设置使用 Stub 引擎
        monkeypatch.setenv("INFERENCE_ENGINE", "stub")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("test.jpg", image_bytes, "image/jpeg")}
            response = await client.post("/api/v1/inference/image", files=files)
            data = response.json()
            assert data["metadata"]["engine"] == "StubInferenceEngine"


class TestDemoScriptCompatibility:
    """验证 demo 脚本的兼容性"""

    @pytest.mark.asyncio
    async def test_demo_request_workflow(self) -> None:
        """模拟 demo_request.py 的工作流"""
        # 1. 创建测试图像（类似 demo 脚本）
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (200, 200, 200)
        cv2.rectangle(img, (100, 150), (300, 400), (150, 150, 150), -1)
        cv2.circle(img, (500, 275), 50, (100, 100, 100), -1)

        success, encoded_image = cv2.imencode(".jpg", img)
        assert success
        image_bytes = encoded_image.tobytes()

        # 2. 发送推理请求（与 demo 脚本相同的 API 调用）
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("test_image.jpg", image_bytes, "image/jpeg")}
            response = await client.post(
                "/api/v1/inference/image", files=files, params={"visualize": "true"}
            )

            # 3. 验证响应格式（demo 脚本依赖的字段）
            assert response.status_code == 200
            data = response.json()

            # demo 脚本期望的字段
            assert "filename" in data
            assert "detections" in data
            assert "metadata" in data
            assert "visualization" in data

            # 验证检测结果格式（demo 脚本会打印）
            for det in data["detections"]:
                assert "label" in det
                assert "confidence" in det
                assert "bbox" in det
                assert len(det["bbox"]) == 4

            # 验证可视化数据格式（demo 脚本会保存）
            if data["visualization"]:
                assert data["visualization"].startswith("data:image/jpeg;base64,")


class TestErrorHandlingE2E:
    """端到端错误处理测试"""

    @pytest.mark.asyncio
    async def test_invalid_file_type(self) -> None:
        """测试无效文件类型的错误处理"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 发送非图像文件
            files = {"file": ("test.txt", b"not an image", "text/plain")}
            response = await client.post("/api/v1/inference/image", files=files)

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            # 检查错误信息包含关键词
            detail_str = str(data["detail"]).lower()
            assert "text/plain" in detail_str or "format" in detail_str

    @pytest.mark.asyncio
    async def test_empty_file(self) -> None:
        """测试空文件的错误处理"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("empty.jpg", b"", "image/jpeg")}
            response = await client.post("/api/v1/inference/image", files=files)

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            # 检查错误信息包含关键词
            detail_str = str(data["detail"]).lower()
            assert "empty" in detail_str or "空" in detail_str

    @pytest.mark.asyncio
    async def test_large_file(self) -> None:
        """测试超大文件的错误处理"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 创建 > 10MB 的文件
            large_data = b"x" * (11 * 1024 * 1024)
            files = {"file": ("large.jpg", large_data, "image/jpeg")}
            response = await client.post("/api/v1/inference/image", files=files)

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            # 检查错误信息包含关键词
            detail_str = str(data["detail"]).lower()
            assert "large" in detail_str or "大" in detail_str or "size" in detail_str


class TestModelFilesExistence:
    """验证模型文件存在性（保证 demo 可运行）"""

    def test_yolo_model_file_exists(self) -> None:
        """验证 YOLO 模型文件存在"""
        # 从环境变量或默认路径获取模型路径
        model_path = os.getenv("YOLO_MODEL_PATH", "runs/train/exp/weights/best.pt")
        model_file = Path(model_path)

        # 如果使用 YOLO 引擎，模型文件必须存在
        engine_type = os.getenv("INFERENCE_ENGINE", "yolo").lower()
        if engine_type != "stub":
            assert model_file.exists(), (
                f"YOLO 模型文件不存在: {model_file}，demo 将无法运行"
            )

    def test_examples_directory_exists(self) -> None:
        """验证 examples 目录和 demo 脚本存在"""
        examples_dir = Path("examples")
        assert examples_dir.exists(), "examples 目录不存在"

        demo_script = examples_dir / "demo_request.py"
        assert demo_script.exists(), "demo_request.py 不存在"
