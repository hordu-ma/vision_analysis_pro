"""HTTP Reporter 稳态与断网恢复回归测试。"""

from __future__ import annotations

from pathlib import Path

import httpx

from vision_analysis_pro.edge_agent import (
    CacheConfig,
    Detection,
    InferenceResult,
    ReporterConfig,
    ReportPayload,
    ReportStatus,
)
from vision_analysis_pro.edge_agent.reporters import HTTPReporter


class _FakeSyncClient:
    def __init__(self, responses: list[httpx.Response | Exception]) -> None:
        self._responses = responses
        self._index = 0

    def post(self, _url: str, json: dict) -> httpx.Response:
        response = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        if isinstance(response, Exception):
            raise response
        return response

    def get(self, _url: str) -> httpx.Response:
        return httpx.Response(200, request=httpx.Request("GET", _url))

    def close(self) -> None:
        return None


def _build_payload(batch_id: str = "edge-agent-001-batch") -> ReportPayload:
    return ReportPayload(
        device_id="edge-agent-001",
        batch_id=batch_id,
        report_time=1700000000.0,
        results=[
            InferenceResult(
                frame_id=1,
                timestamp=1700000000.0,
                source_id="edge-agent-001",
                detections=[
                    Detection(
                        label="crack",
                        confidence=0.95,
                        bbox=[100.0, 150.0, 300.0, 400.0],
                    )
                ],
                inference_time_ms=12.4,
                metadata={"image_name": "tower_001.jpg"},
            )
        ],
    )


def _build_reporter(tmp_path: Path) -> HTTPReporter:
    reporter = HTTPReporter(
        ReporterConfig(
            type="http",
            url="http://example.com/api/v1/report",
            timeout=1.0,
            retry_max=1,
            retry_delay=0.0,
            retry_backoff=1.0,
            batch_size=10,
        ),
        CacheConfig(
            enabled=True,
            db_path=str(tmp_path / "edge-agent-cache.db"),
            max_entries=10,
            max_age_hours=24.0,
            flush_interval=1.0,
        ),
    )
    reporter.connect()
    return reporter


def test_http_reporter_caches_payload_when_network_is_unavailable(
    tmp_path: Path,
) -> None:
    """测试断网时上报结果会落入离线缓存。"""
    reporter = _build_reporter(tmp_path)
    request = httpx.Request("POST", reporter.config.url)
    reporter._sync_client = _FakeSyncClient(  # type: ignore[assignment]
        [httpx.ConnectError("offline", request=request)]
    )

    try:
        status = reporter.report_sync(_build_payload())

        assert status == ReportStatus.CACHED
        assert reporter.get_cache_stats()["count"] == 1
    finally:
        reporter.disconnect()


def test_http_reporter_flushes_cached_payload_after_service_recovers(
    tmp_path: Path,
) -> None:
    """测试服务恢复后缓存中的批次可以成功回放。"""
    reporter = _build_reporter(tmp_path)
    request = httpx.Request("POST", reporter.config.url)
    reporter._sync_client = _FakeSyncClient(  # type: ignore[assignment]
        [httpx.ConnectError("offline", request=request)]
    )

    try:
        first_status = reporter.report_sync(_build_payload())
        assert first_status == ReportStatus.CACHED
        assert reporter.get_cache_stats()["count"] == 1

        reporter._sync_client = _FakeSyncClient(  # type: ignore[assignment]
            [
                httpx.Response(
                    202,
                    request=request,
                    json={"status": "accepted", "batch_id": "edge-agent-001-batch"},
                )
            ]
        )

        flushed = reporter.flush_cache_sync()

        assert flushed == 1
        assert reporter.get_cache_stats()["count"] == 0
    finally:
        reporter.disconnect()


def test_http_reporter_treats_duplicate_batch_as_successful_replay(
    tmp_path: Path,
) -> None:
    """测试重复批次回放收到 duplicate 响应时仍会清理缓存。"""
    reporter = _build_reporter(tmp_path)
    payload = _build_payload(batch_id="edge-agent-001-duplicate")

    try:
        assert reporter._cache is not None
        reporter._cache.add(payload)
        assert reporter.get_cache_stats()["count"] == 1

        reporter._sync_client = _FakeSyncClient(  # type: ignore[assignment]
            [
                httpx.Response(
                    202,
                    request=httpx.Request("POST", reporter.config.url),
                    json={
                        "status": "duplicate",
                        "message": "重复批次已忽略",
                        "batch_id": payload.batch_id,
                    },
                )
            ]
        )

        flushed = reporter.flush_cache_sync()

        assert flushed == 1
        assert reporter.get_cache_stats()["count"] == 0
    finally:
        reporter.disconnect()
