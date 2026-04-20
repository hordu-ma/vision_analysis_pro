"""Tests for template report generation."""

from vision_analysis_pro.edge_agent import Detection, InferenceResult, ReportPayload
from vision_analysis_pro.web.api.report_store import (
    ReportDeviceMetadata,
    ReportFrameReview,
    ReportStoreSaveResult,
)
from vision_analysis_pro.web.api.reporting import (
    REPORT_OUTPUT_SCHEMA_VERSION,
    REPORT_PROMPT_VERSION,
    build_detection_report,
)
from vision_analysis_pro.web.api.schemas import ReportPayloadRequest


def _build_record(
    *,
    label: str = "crack",
    confidence: float = 0.91,
    metadata: dict | None = None,
) -> ReportStoreSaveResult:
    if metadata is None:
        metadata = {"image_name": "tower_001.jpg"}
    payload = ReportPayload(
        device_id="edge-agent-001",
        batch_id="batch-report-001",
        report_time=1700000000.0,
        results=[
            InferenceResult(
                frame_id=1,
                timestamp=1700000000.0,
                source_id="edge-agent-001",
                detections=[
                    Detection(
                        label=label,
                        confidence=confidence,
                        bbox=[1.0, 2.0, 30.0, 40.0],
                    )
                ],
                inference_time_ms=10.0,
                metadata=metadata,
            )
        ],
    )
    request = ReportPayloadRequest.model_validate(payload.to_dict())
    return ReportStoreSaveResult(
        created=True,
        batch_id=request.batch_id,
        device_id=request.device_id,
        report_time=request.report_time,
        result_count=len(request.results),
        total_detections=sum(len(item.detections) for item in request.results),
        payload=request.model_dump(mode="json"),
        created_at=1700000001.0,
    )


def test_build_detection_report_returns_template_summary() -> None:
    report = build_detection_report(_build_record())

    assert report["generated_by"] == "template"
    assert report["prompt_version"] == REPORT_PROMPT_VERSION
    assert report["output_schema_version"] == REPORT_OUTPUT_SCHEMA_VERSION
    assert report["risk_level"] == "high"
    assert report["finding_count"] == 1
    assert report["findings"][0]["label"] == "crack"
    assert report["findings"][0]["label_cn"] == "裂缝"
    assert report["llm_context"]["batch_id"] == "batch-report-001"
    assert report["llm_context"]["prompt"]["version"] == REPORT_PROMPT_VERSION


def test_build_detection_report_llm_mode_preserves_source_facts() -> None:
    report = build_detection_report(
        _build_record(confidence=0.35, metadata={}),
        generation_mode="llm",
    )

    assert report["generated_by"] == "llm"
    assert report["prompt_version"] == REPORT_PROMPT_VERSION
    assert report["output_schema_version"] == REPORT_OUTPUT_SCHEMA_VERSION
    assert report["findings"][0]["label"] == "crack"
    assert report["findings"][0]["max_confidence"] == 0.35
    assert report["llm_context"]["low_confidence_detections"] == [
        {"frame_id": 1, "label": "crack", "confidence": 0.35}
    ]
    assert "device_metadata" in report["llm_context"]["missing_metadata"]
    assert "frame:1:image_name" in report["llm_context"]["missing_metadata"]
    assert any("低置信度" in item for item in report["recommendations"])
    assert any("元数据" in item for item in report["recommendations"])


def test_build_detection_report_llm_mode_uses_review_and_device_metadata() -> None:
    report = build_detection_report(
        _build_record(confidence=0.88),
        {
            1: ReportFrameReview(
                batch_id="batch-report-001",
                frame_id=1,
                status="confirmed",
                note="人工确认",
                reviewer="qa",
                updated_at=1700000002.0,
            )
        },
        device_metadata=ReportDeviceMetadata(
            device_id="edge-agent-001",
            site_name="一号站点",
            display_name="东塔相机",
            note="重点巡检位",
            updated_at=1700000002.0,
        ),
        generation_mode="llm",
    )

    assert report["generated_by"] == "llm"
    assert "一号站点" in report["summary"]
    assert "东塔相机" in report["summary"]
    assert report["llm_context"]["review_counts"] == {"confirmed": 1, "pending": 0}
    assert report["llm_context"]["device_metadata"]["present"] is True
    assert report["llm_context"]["missing_metadata"] == []
