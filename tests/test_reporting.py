"""Tests for template report generation."""

from vision_analysis_pro.edge_agent import Detection, InferenceResult, ReportPayload
from vision_analysis_pro.web.api.report_store import ReportStoreSaveResult
from vision_analysis_pro.web.api.reporting import build_detection_report
from vision_analysis_pro.web.api.schemas import ReportPayloadRequest


def _build_record(label: str = "crack") -> ReportStoreSaveResult:
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
                        confidence=0.91,
                        bbox=[1.0, 2.0, 30.0, 40.0],
                    )
                ],
                inference_time_ms=10.0,
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
    assert report["risk_level"] == "high"
    assert report["finding_count"] == 1
    assert report["findings"][0]["label"] == "crack"
    assert report["findings"][0]["label_cn"] == "裂缝"
    assert report["llm_context"]["batch_id"] == "batch-report-001"
