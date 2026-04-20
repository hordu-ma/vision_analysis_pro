"""Template report generation for persisted edge batches."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from vision_analysis_pro.categories import LABEL_CN, SEVERITY_LEVEL
from vision_analysis_pro.web.api.report_store import (
    ReportDeviceMetadata,
    ReportFrameReview,
    ReportStoreSaveResult,
)

RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
REPORT_PROMPT_VERSION = "inspection-report-prompt.v1"
REPORT_OUTPUT_SCHEMA_VERSION = "inspection-report-output.v1"
LOW_CONFIDENCE_THRESHOLD = 0.6


def build_detection_report(
    record: ReportStoreSaveResult,
    reviews: dict[int, ReportFrameReview] | None = None,
    *,
    device_metadata: ReportDeviceMetadata | None = None,
    generation_mode: str = "template",
    llm_provider: str = "local",
) -> dict[str, Any]:
    """Build a deterministic report draft from one stored report batch."""
    detections_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    frame_count = 0
    for result in record.payload.get("results", []):
        frame_count += 1
        for detection in result.get("detections", []):
            label = str(detection.get("label", "unknown"))
            detections_by_label[label].append(detection)

    findings = [
        _build_finding(label, items) for label, items in detections_by_label.items()
    ]
    findings.sort(
        key=lambda item: (
            RISK_ORDER.get(str(item["risk_level"]), 0),
            float(item["max_confidence"]),
            int(item["count"]),
        ),
        reverse=True,
    )

    risk_level = findings[0]["risk_level"] if findings else "none"
    review_counts = _review_counts(reviews or {})
    missing_metadata = _missing_metadata(record, device_metadata=device_metadata)
    low_confidence_detections = _low_confidence_detections(record)
    llm_context = {
        "batch_id": record.batch_id,
        "device_id": record.device_id,
        "report_time": record.report_time,
        "frame_count": frame_count,
        "total_detections": record.total_detections,
        "risk_level": risk_level,
        "findings": findings,
        "review_counts": review_counts,
        "device_metadata": _device_metadata_context(record, device_metadata),
        "missing_metadata": missing_metadata,
        "low_confidence_detections": low_confidence_detections,
        "prompt": _llm_prompt_contract(),
        "output_schema": _llm_output_schema(),
        "guardrails": [
            "Do not change detection labels, confidence values, bbox values, review status, or device metadata.",
            "Mention missing metadata and low-confidence detections as uncertainty, not as confirmed defects.",
        ],
    }
    summary = _summary_text(record, frame_count=frame_count, risk_level=risk_level)
    recommendations = _recommendations(risk_level, findings, review_counts)
    generated_by = "template"

    if generation_mode == "llm":
        llm_output = _render_local_llm_report(
            record,
            frame_count=frame_count,
            risk_level=risk_level,
            findings=findings,
            review_counts=review_counts,
            missing_metadata=missing_metadata,
            low_confidence_detections=low_confidence_detections,
            device_metadata=device_metadata,
            provider=llm_provider,
        )
        summary = llm_output["summary"]
        recommendations = llm_output["recommendations"]
        generated_by = "llm"

    return {
        "title": f"{record.device_id} 巡检批次报告",
        "summary": summary,
        "risk_level": risk_level,
        "finding_count": len(findings),
        "total_detections": record.total_detections,
        "findings": findings,
        "recommendations": recommendations,
        "llm_context": llm_context,
        "prompt_version": REPORT_PROMPT_VERSION,
        "output_schema_version": REPORT_OUTPUT_SCHEMA_VERSION,
        "generated_by": generated_by,
    }


def _build_finding(label: str, detections: list[dict[str, Any]]) -> dict[str, Any]:
    confidences = [float(item.get("confidence", 0.0)) for item in detections]
    max_confidence = max(confidences, default=0.0)
    risk_level = _risk_for_label(label, max_confidence)
    return {
        "label": label,
        "label_cn": LABEL_CN.get(label, label),
        "count": len(detections),
        "max_confidence": round(max_confidence, 4),
        "risk_level": risk_level,
        "action": _action_for_risk(risk_level),
    }


def _risk_for_label(label: str, confidence: float) -> str:
    severity = SEVERITY_LEVEL.get(label, "medium")
    if severity == "high" and confidence >= 0.6:
        return "high"
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.4:
        return "medium"
    return "low"


def _action_for_risk(risk_level: str) -> str:
    if risk_level == "high":
        return "优先安排人工复核，并结合现场照片确认处置优先级。"
    if risk_level == "medium":
        return "纳入近期复核清单，补充同位置多角度图像。"
    if risk_level == "low":
        return "作为低优先级线索留存，等待更多样本确认。"
    return "当前无需处置，保留巡检记录。"


def _summary_text(
    record: ReportStoreSaveResult,
    *,
    frame_count: int,
    risk_level: str,
) -> str:
    if record.total_detections == 0:
        return f"批次 {record.batch_id} 共接收 {frame_count} 帧，未发现可报告缺陷。"
    risk_text = {
        "high": "存在高优先级缺陷线索",
        "medium": "存在中等优先级缺陷线索",
        "low": "存在低优先级缺陷线索",
    }.get(risk_level, "未形成明确风险等级")
    return (
        f"批次 {record.batch_id} 共接收 {frame_count} 帧，"
        f"检测到 {record.total_detections} 个缺陷候选，{risk_text}。"
    )


def _recommendations(
    risk_level: str,
    findings: list[dict[str, Any]],
    review_counts: dict[str, int],
) -> list[str]:
    if not findings:
        return ["保留本批次作为巡检记录；如现场风险较高，可补充近距离复拍。"]

    recommendations = [_action_for_risk(risk_level)]
    labels = "、".join(str(item["label_cn"]) for item in findings[:3])
    recommendations.append(f"优先复核类别：{labels}。")

    if review_counts.get("pending", 0) > 0:
        recommendations.append("仍有待复核帧，报告结论应在复核完成后再对外发布。")
    else:
        recommendations.append("可将本模板摘要作为 LLM 报告生成的结构化输入。")
    return recommendations


def _review_counts(reviews: dict[int, ReportFrameReview]) -> dict[str, int]:
    counts = Counter(review.status for review in reviews.values())
    if reviews and "pending" not in counts:
        counts["pending"] = 0
    return dict(counts)


def _device_metadata_context(
    record: ReportStoreSaveResult,
    metadata: ReportDeviceMetadata | None,
) -> dict[str, Any]:
    if metadata is None:
        return {
            "device_id": record.device_id,
            "site_name": "",
            "display_name": "",
            "note": "",
            "present": False,
        }
    return {
        "device_id": metadata.device_id,
        "site_name": metadata.site_name,
        "display_name": metadata.display_name,
        "note": metadata.note,
        "updated_at": metadata.updated_at,
        "present": any([metadata.site_name, metadata.display_name, metadata.note]),
    }


def _missing_metadata(
    record: ReportStoreSaveResult,
    *,
    device_metadata: ReportDeviceMetadata | None,
) -> list[str]:
    missing: list[str] = []
    metadata_context = _device_metadata_context(record, device_metadata)
    if not metadata_context["present"]:
        missing.append("device_metadata")

    for result in record.payload.get("results", []):
        frame_metadata = result.get("metadata") or {}
        if not frame_metadata.get("image_name"):
            frame_id = result.get("frame_id", "unknown")
            missing.append(f"frame:{frame_id}:image_name")
    return missing


def _low_confidence_detections(record: ReportStoreSaveResult) -> list[dict[str, Any]]:
    detections: list[dict[str, Any]] = []
    for result in record.payload.get("results", []):
        frame_id = int(result.get("frame_id", 0))
        for detection in result.get("detections", []):
            confidence = float(detection.get("confidence", 0.0))
            if confidence < LOW_CONFIDENCE_THRESHOLD:
                detections.append(
                    {
                        "frame_id": frame_id,
                        "label": str(detection.get("label", "unknown")),
                        "confidence": round(confidence, 4),
                    }
                )
    return detections


def _llm_prompt_contract() -> dict[str, Any]:
    return {
        "version": REPORT_PROMPT_VERSION,
        "system": (
            "You write inspection report text from structured detection facts. "
            "You must preserve source labels, confidence values, bbox values, "
            "review status, and device metadata exactly."
        ),
        "user": (
            "Use llm_context to write a concise inspection report summary and "
            "action recommendations. Call out missing metadata and low-confidence "
            "detections as uncertainty."
        ),
    }


def _llm_output_schema() -> dict[str, Any]:
    return {
        "version": REPORT_OUTPUT_SCHEMA_VERSION,
        "type": "object",
        "required": ["summary", "recommendations", "risk_level", "source_facts"],
        "properties": {
            "summary": {"type": "string"},
            "recommendations": {"type": "array", "items": {"type": "string"}},
            "risk_level": {"type": "string", "enum": ["none", "low", "medium", "high"]},
            "source_facts": {
                "type": "object",
                "required": ["batch_id", "device_id", "findings"],
            },
        },
    }


def _render_local_llm_report(
    record: ReportStoreSaveResult,
    *,
    frame_count: int,
    risk_level: str,
    findings: list[dict[str, Any]],
    review_counts: dict[str, int],
    missing_metadata: list[str],
    low_confidence_detections: list[dict[str, Any]],
    device_metadata: ReportDeviceMetadata | None,
    provider: str,
) -> dict[str, Any]:
    if provider != "local":
        raise ValueError(f"Unsupported report LLM provider: {provider}")

    device_name = record.device_id
    site_clause = "设备元数据缺失"
    if device_metadata and device_metadata.display_name:
        device_name = device_metadata.display_name
    if device_metadata and device_metadata.site_name:
        site_clause = f"站点 {device_metadata.site_name}"

    if findings:
        finding_text = "、".join(
            f"{item['label_cn']} {item['count']} 处，最高置信度 {item['max_confidence']}"
            for item in findings[:3]
        )
    else:
        finding_text = "未发现可报告缺陷"

    uncertainty_parts: list[str] = []
    if missing_metadata:
        uncertainty_parts.append("存在元数据缺失")
    if low_confidence_detections:
        uncertainty_parts.append("存在低置信度候选")
    uncertainty_text = (
        "；".join(uncertainty_parts) if uncertainty_parts else "输入信息完整"
    )

    review_text = "尚无人工复核记录"
    if review_counts:
        review_text = "，".join(
            f"{status}:{count}" for status, count in sorted(review_counts.items())
        )

    summary = (
        f"{site_clause} 的 {device_name} 在批次 {record.batch_id} 共上报 {frame_count} 帧，"
        f"检测候选总数 {record.total_detections}，整体风险等级为 {risk_level}。"
        f"主要发现：{finding_text}。复核状态：{review_text}。{uncertainty_text}。"
    )

    recommendations = _recommendations(risk_level, findings, review_counts)
    if low_confidence_detections:
        recommendations.append("低置信度候选仅作为复核线索，需结合原图或复拍确认。")
    if missing_metadata:
        recommendations.append("补齐设备、站点或帧图像元数据后再生成对外报告。")

    return {
        "summary": summary,
        "recommendations": recommendations,
        "risk_level": risk_level,
        "source_facts": {
            "batch_id": record.batch_id,
            "device_id": record.device_id,
            "findings": findings,
        },
    }
