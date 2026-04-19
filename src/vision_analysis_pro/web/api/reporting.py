"""Template report generation for persisted edge batches."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from vision_analysis_pro.categories import LABEL_CN, SEVERITY_LEVEL
from vision_analysis_pro.web.api.report_store import (
    ReportFrameReview,
    ReportStoreSaveResult,
)

RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def build_detection_report(
    record: ReportStoreSaveResult,
    reviews: dict[int, ReportFrameReview] | None = None,
) -> dict[str, Any]:
    """Build a deterministic report draft from one stored report batch."""
    detections_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    frame_count = 0
    for result in record.payload.get("results", []):
        frame_count += 1
        for detection in result.get("detections", []):
            label = str(detection.get("label", "unknown"))
            detections_by_label[label].append(detection)

    findings = [_build_finding(label, items) for label, items in detections_by_label.items()]
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
    summary = _summary_text(record, frame_count=frame_count, risk_level=risk_level)

    return {
        "title": f"{record.device_id} 巡检批次报告",
        "summary": summary,
        "risk_level": risk_level,
        "finding_count": len(findings),
        "total_detections": record.total_detections,
        "findings": findings,
        "recommendations": _recommendations(risk_level, findings, review_counts),
        "llm_context": {
            "batch_id": record.batch_id,
            "device_id": record.device_id,
            "report_time": record.report_time,
            "frame_count": frame_count,
            "total_detections": record.total_detections,
            "risk_level": risk_level,
            "findings": findings,
            "review_counts": review_counts,
        },
        "generated_by": "template",
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
        return (
            f"批次 {record.batch_id} 共接收 {frame_count} 帧，未发现可报告缺陷。"
        )
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
