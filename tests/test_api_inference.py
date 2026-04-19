"""API 层测试"""

import asyncio
import base64
import re
from pathlib import Path

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from vision_analysis_pro.core.inference.stub_engine import StubInferenceEngine
from vision_analysis_pro.edge_agent import Detection, InferenceResult, ReportPayload
from vision_analysis_pro.settings import Settings, get_settings
from vision_analysis_pro.web.api.deps import get_inference_engine
from vision_analysis_pro.web.api.inference_tasks import clear_inference_task_manager
from vision_analysis_pro.web.api.main import app
from vision_analysis_pro.web.api.report_store import clear_report_store_cache


def _create_test_image() -> bytes:
    """创建一个简单的测试图像"""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:] = (128, 128, 128)  # 灰色
    success, encoded = cv2.imencode(".jpg", img)
    assert success
    return encoded.tobytes()


def _create_report_payload(
    *,
    batch_id: str = "edge-agent-001-test-batch",
    device_id: str = "edge-agent-001",
    label: str = "crack",
) -> dict:
    """创建与 Edge Agent 实际序列化格式一致的上报载荷。"""
    payload = ReportPayload(
        device_id=device_id,
        batch_id=batch_id,
        report_time=1700000000.0,
        results=[
            InferenceResult(
                frame_id=1,
                timestamp=1700000000.0,
                source_id=device_id,
                detections=[
                    Detection(
                        label=label,
                        confidence=0.95,
                        bbox=[100.0, 150.0, 300.0, 400.0],
                    )
                ],
                inference_time_ms=12.4,
                metadata={"image_name": "tower_001.jpg"},
            )
        ],
    )
    return payload.to_dict()


@pytest.fixture(autouse=True)
def override_dependencies(tmp_path: Path):
    """在测试期间覆盖依赖（使用 stub 引擎）"""
    original_overrides = app.dependency_overrides.copy()
    clear_report_store_cache()
    clear_inference_task_manager()

    def _fake_settings() -> Settings:
        return Settings.model_validate(
            {
                "model_path": "models/fake.pt",
                "confidence_threshold": 0.5,
                "iou_threshold": 0.5,
                "cloud_api_key": "",
                "report_store_db_path": str(tmp_path / "reports.db"),
            }
        )

    app.dependency_overrides[get_settings] = _fake_settings
    app.dependency_overrides[get_inference_engine] = lambda: StubInferenceEngine(
        mode="normal"
    )

    yield
    app.dependency_overrides = original_overrides
    clear_report_store_cache()
    clear_inference_task_manager()


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


@pytest.mark.asyncio
async def test_inference_endpoint_with_visualization() -> None:
    """测试带可视化的推理接口"""
    # 恢复 normal 模式
    app.dependency_overrides[get_inference_engine] = lambda: StubInferenceEngine(
        mode="normal"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 创建真实图像用于可视化
        test_image = _create_test_image()

        resp = await client.post(
            "/api/v1/inference/image?visualize=true",
            files={"file": ("test.jpg", test_image, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()

        # 验证基本响应
        assert data["filename"] == "test.jpg"
        assert len(data["detections"]) == 3

        # 验证可视化字段存在
        assert "visualization" in data
        assert data["visualization"] is not None

        # 验证 base64 格式
        assert data["visualization"].startswith("data:image/jpeg;base64,")

        # 验证可以解码 base64
        base64_data = data["visualization"].split(",")[1]
        decoded_bytes = base64.b64decode(base64_data)
        assert len(decoded_bytes) > 0

        # 验证解码后的图像有效
        nparr = np.frombuffer(decoded_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None


@pytest.mark.asyncio
async def test_inference_endpoint_without_visualization() -> None:
    """测试不带可视化的推理接口（默认行为）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_image = _create_test_image()

        resp = await client.post(
            "/api/v1/inference/image",
            files={"file": ("test.jpg", test_image, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()

        # 验证基本响应
        assert data["filename"] == "test.jpg"
        assert len(data["detections"]) == 3

        # 验证 visualization 字段为 None（默认不返回）
        assert data.get("visualization") is None


@pytest.mark.asyncio
async def test_batch_inference_endpoint_returns_multiple_results() -> None:
    """测试批量推理接口返回逐文件结果。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/images?visualize=false",
            files=[
                ("files", ("first.jpg", _create_test_image(), "image/jpeg")),
                ("files", ("second.jpg", _create_test_image(), "image/jpeg")),
            ],
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["metadata"]["file_count"] == 2
    assert len(data["files"]) == 2
    assert data["files"][0]["filename"] == "first.jpg"
    assert data["files"][1]["filename"] == "second.jpg"
    assert len(data["files"][0]["detections"]) == 3


@pytest.mark.asyncio
async def test_batch_inference_endpoint_rejects_empty_uploads() -> None:
    """测试批量推理接口拒绝空文件。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/images",
            files=[("files", ("empty.jpg", b"", "image/jpeg"))],
        )

    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == "EMPTY_FILE"


@pytest.mark.asyncio
async def test_create_inference_task_returns_completed_task_for_stub_engine() -> None:
    """测试创建异步批量任务并查询结果。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/inference/images/tasks?visualize=false",
            files=[
                ("files", ("first.jpg", _create_test_image(), "image/jpeg")),
                ("files", ("second.jpg", _create_test_image(), "image/jpeg")),
            ],
        )

        assert create_resp.status_code == 202
        task_id = create_resp.json()["task_id"]

        for _ in range(20):
            task_resp = await client.get(f"/api/v1/inference/images/tasks/{task_id}")
            assert task_resp.status_code == 200
            task_data = task_resp.json()
            if task_data["status"] == "completed":
                break
            await asyncio.sleep(0.01)
        else:
            pytest.fail("异步推理任务未在预期时间内完成")

    assert task_data["file_count"] == 2
    assert task_data["completed_files"] == 2
    assert task_data["progress"] == 100
    assert len(task_data["results"]) == 2


@pytest.mark.asyncio
async def test_get_inference_task_returns_not_found_for_missing_task() -> None:
    """测试查询不存在的推理任务返回 404。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/inference/images/tasks/task-missing")

    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "TASK_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_inference_tasks_returns_recent_tasks() -> None:
    """测试任务列表接口按创建时间倒序返回任务。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first_resp = await client.post(
            "/api/v1/inference/images/tasks?visualize=false",
            files=[("files", ("first.jpg", _create_test_image(), "image/jpeg"))],
        )
        second_resp = await client.post(
            "/api/v1/inference/images/tasks?visualize=false",
            files=[("files", ("second.jpg", _create_test_image(), "image/jpeg"))],
        )
        assert first_resp.status_code == 202
        assert second_resp.status_code == 202

        resp = await client.get("/api/v1/inference/images/tasks?limit=10")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["task_id"] == second_resp.json()["task_id"]
    assert data[1]["task_id"] == first_resp.json()["task_id"]


@pytest.mark.asyncio
async def test_live_health_endpoint() -> None:
    """测试存活检查端点"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health/live")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"
    assert data["version"] == app.version


@pytest.mark.asyncio
async def test_ready_health_endpoint() -> None:
    """测试就绪检查端点"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health/ready")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"ready", "degraded"}
    assert "engine" in data
    assert "model_loaded" in data


@pytest.mark.asyncio
async def test_metrics_endpoint() -> None:
    """测试 metrics 端点返回基础指标"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/metrics")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    body = resp.text
    assert "vision_api_requests_total" in body
    assert "vision_api_request_duration_ms_count" in body
    assert "vision_api_inference_requests_total" in body
    assert "vision_api_inference_failures_total" in body
    assert "vision_api_request_status_total" in body


@pytest.mark.asyncio
async def test_report_endpoint_accepts_edge_agent_payload() -> None:
    """测试 report 端点接收 Edge Agent 实际上报载荷"""
    request_id = "req-test-report-001"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/report",
            headers={"x-request-id": request_id},
            json=_create_report_payload(),
        )

    assert resp.status_code == 202
    assert resp.headers["x-request-id"] == request_id
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["batch_id"] == "edge-agent-001-test-batch"
    assert data["result_count"] == 1
    assert data["total_detections"] == 1
    assert data["request_id"] == request_id


@pytest.mark.asyncio
async def test_report_endpoint_accepts_empty_result_batch() -> None:
    """测试 report 端点允许空批次，便于心跳或空检测批次扩展"""
    payload = {
        "device_id": "edge-agent-001",
        "batch_id": "edge-agent-001-empty-batch",
        "report_time": 1700000000.0,
        "results": [],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/report", json=payload)

    assert resp.status_code == 202
    data = resp.json()
    assert data["batch_id"] == "edge-agent-001-empty-batch"
    assert data["result_count"] == 0
    assert data["total_detections"] == 0


@pytest.mark.asyncio
async def test_report_endpoint_persists_payload() -> None:
    """测试 report 端点持久化 Edge Agent 上报载荷"""
    payload = _create_report_payload()
    request_id = "req-test-report-get-001"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        post_resp = await client.post("/api/v1/report", json=payload)
        get_resp = await client.get(
            f"/api/v1/report/{payload['batch_id']}",
            headers={"x-request-id": request_id},
        )

    assert post_resp.status_code == 202
    assert get_resp.status_code == 200
    assert get_resp.headers["x-request-id"] == request_id
    data = get_resp.json()
    assert data["status"] == "found"
    assert data["batch_id"] == payload["batch_id"]
    assert data["device_id"] == payload["device_id"]
    assert data["result_count"] == 1
    assert data["total_detections"] == 1
    assert data["payload"] == payload
    assert data["request_id"] == request_id


@pytest.mark.asyncio
async def test_report_endpoint_returns_duplicate_for_existing_batch() -> None:
    """测试重复 batch_id 按幂等重复请求处理"""
    payload = _create_report_payload()
    start_requests = app.state.metrics["report_requests_total"]
    start_results = app.state.metrics["report_results_total"]
    start_detections = app.state.metrics["report_detections_total"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first_resp = await client.post("/api/v1/report", json=payload)
        second_resp = await client.post("/api/v1/report", json=payload)

    assert first_resp.status_code == 202
    assert first_resp.json()["status"] == "accepted"
    assert second_resp.status_code == 202
    second_data = second_resp.json()
    assert second_data["status"] == "duplicate"
    assert second_data["message"] == "重复批次已忽略"
    assert second_data["result_count"] == 1
    assert second_data["total_detections"] == 1
    assert app.state.metrics["report_requests_total"] == start_requests + 2
    assert app.state.metrics["report_results_total"] == start_results + 1
    assert app.state.metrics["report_detections_total"] == start_detections + 1


@pytest.mark.asyncio
async def test_report_endpoint_requires_api_key_when_configured(
    tmp_path: Path,
) -> None:
    """测试配置 CLOUD_API_KEY 后 report 端点要求鉴权"""
    payload = _create_report_payload()

    def _secure_settings() -> Settings:
        return Settings.model_validate(
            {
                "model_path": "models/fake.pt",
                "confidence_threshold": 0.5,
                "iou_threshold": 0.5,
                "cloud_api_key": "secret",
                "report_store_db_path": str(tmp_path / "secure-reports.db"),
            }
        )

    app.dependency_overrides[get_settings] = _secure_settings
    clear_report_store_cache()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized_resp = await client.post("/api/v1/report", json=payload)
        authorized_resp = await client.post(
            "/api/v1/report",
            headers={"authorization": "Bearer secret"},
            json=payload,
        )

    assert unauthorized_resp.status_code == 401
    unauthorized_data = unauthorized_resp.json()
    assert unauthorized_data["code"] == "UNAUTHORIZED"
    assert unauthorized_data["message"] == "未授权上报"
    assert authorized_resp.status_code == 202
    assert authorized_resp.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_report_endpoint_returns_not_found_for_missing_batch() -> None:
    """测试查询不存在的上报批次返回统一 404 错误"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/report/missing-batch")

    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "REPORT_NOT_FOUND"
    assert data["message"] == "上报批次不存在"


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_report_counters() -> None:
    """测试 metrics 端点暴露边缘上报计数器"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/v1/report", json=_create_report_payload())
        resp = await client.get("/api/v1/metrics")

    assert resp.status_code == 200
    body = resp.text
    assert "vision_api_report_requests_total" in body
    assert "vision_api_report_query_requests_total" in body
    assert "vision_api_report_results_total" in body
    assert "vision_api_report_detections_total" in body
    assert "vision_api_report_duplicates_total" in body


@pytest.mark.asyncio
async def test_inference_endpoint_returns_request_id_header() -> None:
    """测试推理接口返回 request id 响应头"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/image",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    assert resp.status_code == 200
    request_id = resp.headers.get("x-request-id")
    assert request_id is not None
    assert request_id != ""


@pytest.mark.asyncio
async def test_inference_endpoint_metadata_contains_observability_fields() -> None:
    """测试推理响应元数据包含基础观测字段"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/image",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    assert resp.status_code == 200
    data = resp.json()
    metadata = data["metadata"]

    assert metadata["engine"] == "StubInferenceEngine"
    assert "request_id" in metadata
    assert metadata["request_id"]
    assert "inference_time_ms" in metadata
    assert isinstance(metadata["inference_time_ms"], (int, float))
    assert metadata["inference_time_ms"] >= 0
    assert "detection_count" in metadata
    assert metadata["detection_count"] == 3


@pytest.mark.asyncio
async def test_health_endpoints_include_request_id_and_check_type() -> None:
    """测试健康检查端点返回 request_id 与检查类型"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        live_resp = await client.get("/api/v1/health/live")
        ready_resp = await client.get("/api/v1/health/ready")

    assert live_resp.status_code == 200
    live_data = live_resp.json()
    assert live_data["check"] == "live"
    assert live_data["request_id"] == live_resp.headers["x-request-id"]

    assert ready_resp.status_code in {200, 503}
    ready_data = ready_resp.json()
    assert ready_data["check"] == "ready"
    assert ready_data["request_id"] == ready_resp.headers["x-request-id"]


@pytest.mark.asyncio
async def test_request_id_is_propagated_from_request_header() -> None:
    """测试请求头中的 request id 会透传到响应头与响应体"""
    request_id = "req-test-observability-001"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/image",
            headers={"x-request-id": request_id},
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    assert resp.status_code == 200
    assert resp.headers["x-request-id"] == request_id
    assert resp.json()["metadata"]["request_id"] == request_id


@pytest.mark.asyncio
async def test_error_response_contains_request_id_header_and_body() -> None:
    """测试错误响应同时包含 request_id 响应头与响应体字段"""
    request_id = "req-test-error-001"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/inference/image",
            headers={"x-request-id": request_id},
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )

    assert resp.status_code == 400
    data = resp.json()
    assert resp.headers["x-request-id"] == request_id
    assert data["request_id"] == request_id
    assert data["code"] == "EMPTY_FILE"


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_health_check_counters() -> None:
    """测试 metrics 端点暴露健康检查计数器"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/v1/health/live")
        await client.get("/api/v1/health/ready")
        resp = await client.get("/api/v1/metrics")

    assert resp.status_code == 200
    body = resp.text
    assert "vision_api_health_live_checks_total" in body
    assert "vision_api_health_ready_checks_total" in body


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_non_negative_counter_values() -> None:
    """测试 metrics 端点中的关键计数器值为非负数"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/inference/image",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )
        resp = await client.get("/api/v1/metrics")

    assert resp.status_code == 200
    body = resp.text

    metric_names = [
        "vision_api_requests_total",
        "vision_api_requests_in_flight",
        "vision_api_requests_failed_total",
        "vision_api_inference_requests_total",
        "vision_api_inference_failures_total",
        "vision_api_request_duration_ms_count",
        "vision_api_inference_duration_ms_count",
    ]
    for metric_name in metric_names:
        match = re.search(rf"{metric_name} (\d+)", body)
        assert match is not None
        assert int(match.group(1)) >= 0


@pytest.mark.asyncio
async def test_inference_error_increments_failure_metric() -> None:
    """测试推理失败后 metrics 中失败计数器存在"""
    app.dependency_overrides[get_inference_engine] = lambda: StubInferenceEngine(
        mode="error"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        error_resp = await client.post(
            "/api/v1/inference/image",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )
        metrics_resp = await client.get("/api/v1/metrics")

    assert error_resp.status_code == 500
    assert metrics_resp.status_code == 200
    assert "vision_api_inference_failures_total" in metrics_resp.text


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_request_status_labels() -> None:
    """测试 metrics 端点按 method/path/status_code 输出请求计数。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/v1/health")
        resp = await client.get("/api/v1/metrics")

    assert resp.status_code == 200
    assert (
        'vision_api_request_status_total{method="GET",path="/api/v1/health",status_code="200"}'
        in resp.text
    )


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_inference_observability_counters() -> None:
    """测试推理请求会累加输入大小、耗时和检测数量指标。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/inference/image?visualize=true",
            files={"file": ("test.jpg", _create_test_image(), "image/jpeg")},
        )
        resp = await client.get("/api/v1/metrics")

    body = resp.text
    assert "vision_api_inference_duration_ms_sum" in body
    assert "vision_api_inference_detections_total" in body
    assert "vision_api_inference_visualizations_total" in body
    assert "vision_api_inference_input_bytes_total" in body


@pytest.mark.asyncio
async def test_report_query_and_not_found_metrics_are_exposed() -> None:
    """测试 report 查询与 miss 指标会在 metrics 中暴露。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/v1/report/missing-batch")
        resp = await client.get("/api/v1/metrics")

    assert resp.status_code == 200
    body = resp.text
    assert "vision_api_report_query_requests_total" in body
    assert "vision_api_report_not_found_total" in body


@pytest.mark.asyncio
async def test_report_batches_endpoint_lists_recent_batches() -> None:
    """测试批次列表接口返回最近批次摘要。"""
    first_payload = _create_report_payload(batch_id="batch-001", device_id="device-a")
    second_payload = _create_report_payload(batch_id="batch-002", device_id="device-b")
    request_id = "req-test-report-batches-001"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/v1/report", json=first_payload)
        await client.post("/api/v1/report", json=second_payload)
        resp = await client.get(
            "/api/v1/reports/batches",
            headers={"x-request-id": request_id},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["count"] == 2
    assert data["request_id"] == request_id
    assert data["items"][0]["batch_id"] == "batch-002"
    assert data["items"][1]["batch_id"] == "batch-001"


@pytest.mark.asyncio
async def test_report_batches_endpoint_supports_device_filter() -> None:
    """测试批次列表接口支持按设备过滤。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/report",
            json=_create_report_payload(batch_id="batch-a", device_id="device-a"),
        )
        await client.post(
            "/api/v1/report",
            json=_create_report_payload(batch_id="batch-b", device_id="device-b"),
        )
        resp = await client.get("/api/v1/reports/batches?device_id=device-a")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["items"][0]["device_id"] == "device-a"
    assert data["items"][0]["batch_id"] == "batch-a"


@pytest.mark.asyncio
async def test_report_devices_endpoint_aggregates_by_device() -> None:
    """测试设备概览接口返回按设备聚合的批次统计。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/report",
            json=_create_report_payload(batch_id="device-a-001", device_id="device-a"),
        )
        await client.post(
            "/api/v1/report",
            json=_create_report_payload(
                batch_id="device-a-002",
                device_id="device-a",
                label="rust",
            ),
        )
        await client.post(
            "/api/v1/report",
            json=_create_report_payload(batch_id="device-b-001", device_id="device-b"),
        )
        resp = await client.get("/api/v1/reports/devices")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["count"] == 2

    items_by_device = {item["device_id"]: item for item in data["items"]}
    assert items_by_device["device-a"]["batch_count"] == 2
    assert items_by_device["device-a"]["result_count"] == 2
    assert items_by_device["device-a"]["total_detections"] == 2
    assert items_by_device["device-a"]["last_batch_id"] == "device-a-002"
    assert items_by_device["device-b"]["batch_count"] == 1


@pytest.mark.asyncio
async def test_report_detail_endpoint_includes_frame_results_and_reviews() -> None:
    """测试批次详情接口会返回单帧详情与复核信息。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/report",
            json=_create_report_payload(
                batch_id="detail-batch-001", device_id="device-a"
            ),
        )
        review_resp = await client.put(
            "/api/v1/report/detail-batch-001/reviews/1",
            json={"status": "confirmed", "note": "人工确认裂缝", "reviewer": "alice"},
        )
        assert review_resp.status_code == 200

        resp = await client.get("/api/v1/report/detail-batch-001")

    assert resp.status_code == 200
    data = resp.json()
    assert data["batch_id"] == "detail-batch-001"
    assert len(data["results"]) == 1
    assert data["results"][0]["frame_id"] == 1
    assert data["results"][0]["review"]["status"] == "confirmed"
    assert data["results"][0]["review"]["reviewer"] == "alice"


@pytest.mark.asyncio
async def test_report_review_endpoint_returns_not_found_for_missing_batch() -> None:
    """测试不存在的批次不能写入复核结果。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put(
            "/api/v1/report/missing-batch/reviews/1",
            json={"status": "confirmed", "note": "", "reviewer": "bob"},
        )

    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "REPORT_NOT_FOUND"


@pytest.mark.asyncio
async def test_report_csv_export_endpoint_returns_attachment() -> None:
    """测试批次 CSV 导出接口返回附件内容。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/report",
            json=_create_report_payload(
                batch_id="export-batch-001", device_id="device-a"
            ),
        )
        await client.put(
            "/api/v1/report/export-batch-001/reviews/1",
            json={"status": "false_positive", "note": "误报", "reviewer": "qa"},
        )
        resp = await client.get("/api/v1/report/export-batch-001/export.csv")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert (
        'attachment; filename="export-batch-001.csv"'
        == resp.headers["content-disposition"]
    )
    assert (
        "batch_id,device_id,frame_id,timestamp,image_name,label,confidence,bbox,review_status,review_note,reviewer,review_updated_at"
        in resp.text
    )
    assert "export-batch-001" in resp.text
    assert "false_positive" in resp.text
    assert "误报" in resp.text
