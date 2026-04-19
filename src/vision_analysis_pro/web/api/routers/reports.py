"""边缘 Agent 上报 API"""

import csv
import io
import logging
import time
from secrets import compare_digest

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response

from vision_analysis_pro.settings import Settings, get_settings
from vision_analysis_pro.web.api import schemas
from vision_analysis_pro.web.api.inference_tasks import get_inference_task_manager
from vision_analysis_pro.web.api.report_store import (
    ReportFrameReview,
    ReportStoreSaveResult,
    get_report_store,
)
from vision_analysis_pro.web.api.reporting import build_detection_report

router = APIRouter(prefix="/api/v1", tags=["reports"])
logger = logging.getLogger(__name__)


@router.post(
    "/report",
    response_model=schemas.ReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": schemas.ReportResponse},
        401: {"model": schemas.ErrorResponse},
        422: {"model": schemas.ErrorResponse},
    },
)
async def receive_report(
    request: Request,
    payload: schemas.ReportPayloadRequest,
    settings: Settings = Depends(get_settings),
) -> schemas.ReportResponse:
    """接收边缘 Agent 批量上报结果。

    批次按 batch_id 持久化；重复 batch_id 作为幂等重复请求处理。
    """
    _authorize_report_request(request, settings)
    request_id = getattr(request.state, "request_id", None)
    store = get_report_store(str(settings.report_store_db_path))
    save_result = store.save(payload)

    metrics: dict[str, int | dict[str, int] | float] = request.app.state.metrics
    metrics["report_requests_total"] += 1
    if save_result.created:
        metrics["report_results_total"] += save_result.result_count
        metrics["report_detections_total"] += save_result.total_detections
    else:
        metrics["report_duplicates_total"] += 1

    logger.info(
        "edge_report_received",
        extra={
            "request_id": request_id,
            "device_id": save_result.device_id,
            "batch_id": save_result.batch_id,
            "result_count": save_result.result_count,
            "total_detections": save_result.total_detections,
            "created": save_result.created,
        },
    )

    return schemas.ReportResponse(
        status="accepted" if save_result.created else "duplicate",
        message="上报已接收" if save_result.created else "重复批次已忽略",
        batch_id=save_result.batch_id,
        result_count=save_result.result_count,
        total_detections=save_result.total_detections,
        request_id=request_id,
    )


@router.put(
    "/reports/devices/{device_id}",
    response_model=schemas.ReportDeviceMetadataResponse,
    responses={200: {"model": schemas.ReportDeviceMetadataResponse}},
)
async def upsert_report_device_metadata(
    device_id: str,
    payload: schemas.ReportDeviceMetadataRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> schemas.ReportDeviceMetadataResponse:
    """写入设备元数据。"""
    _authorize_report_request(request, settings)
    request_id = getattr(request.state, "request_id", None) or "unknown"
    store = get_report_store(str(settings.report_store_db_path))
    actor = request.headers.get("x-actor", "system")
    metadata = store.upsert_device_metadata(
        device_id=device_id,
        site_name=payload.site_name,
        display_name=payload.display_name,
        note=payload.note,
    )
    store.append_audit_log(
        event_type="device_metadata_updated",
        resource_id=device_id,
        actor=actor,
        request_id=request_id,
        detail=payload.model_dump(mode="json"),
    )
    return schemas.ReportDeviceMetadataResponse(
        device_id=metadata.device_id,
        site_name=metadata.site_name,
        display_name=metadata.display_name,
        note=metadata.note,
        updated_at=metadata.updated_at,
    )


@router.get(
    "/reports/devices/{device_id}",
    response_model=schemas.ReportDeviceMetadataResponse,
    responses={200: {"model": schemas.ReportDeviceMetadataResponse}},
)
async def get_report_device_metadata(
    device_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> schemas.ReportDeviceMetadataResponse:
    """读取设备元数据。"""
    _authorize_report_request(request, settings)
    store = get_report_store(str(settings.report_store_db_path))
    metadata = store.get_device_metadata(device_id)
    if metadata is None:
        return schemas.ReportDeviceMetadataResponse(
            device_id=device_id,
            site_name="",
            display_name="",
            note="",
            updated_at=0.0,
        )
    return schemas.ReportDeviceMetadataResponse(
        device_id=metadata.device_id,
        site_name=metadata.site_name,
        display_name=metadata.display_name,
        note=metadata.note,
        updated_at=metadata.updated_at,
    )


@router.get(
    "/report/{batch_id}",
    response_model=schemas.ReportRecordResponse,
    responses={
        200: {"model": schemas.ReportRecordResponse},
        401: {"model": schemas.ErrorResponse},
        404: {"model": schemas.ErrorResponse},
    },
)
async def get_report(
    batch_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> schemas.ReportRecordResponse:
    """查询已持久化的边缘 Agent 上报批次。"""
    _authorize_report_request(request, settings)
    request_id = getattr(request.state, "request_id", None)
    request.app.state.metrics["report_query_requests_total"] += 1
    store = get_report_store(str(settings.report_store_db_path))
    record = store.get(batch_id)
    if record is None:
        request.app.state.metrics["report_not_found_total"] += 1
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "REPORT_NOT_FOUND",
                "message": "上报批次不存在",
                "detail": batch_id,
            },
        )

    reviews = store.list_reviews(batch_id)
    return _record_to_response(record, request_id=request_id, reviews=reviews)


@router.get(
    "/report/{batch_id}/summary",
    response_model=schemas.DetectionReportResponse,
    responses={
        200: {"model": schemas.DetectionReportResponse},
        401: {"model": schemas.ErrorResponse},
        404: {"model": schemas.ErrorResponse},
    },
)
async def get_report_summary(
    batch_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> schemas.DetectionReportResponse:
    """生成指定上报批次的模板报告摘要。"""
    _authorize_report_request(request, settings)
    request_id = getattr(request.state, "request_id", None)
    request.app.state.metrics["report_query_requests_total"] += 1
    store = get_report_store(str(settings.report_store_db_path))
    record = store.get(batch_id)
    if record is None:
        request.app.state.metrics["report_not_found_total"] += 1
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "REPORT_NOT_FOUND",
                "message": "上报批次不存在",
                "detail": batch_id,
            },
        )

    report = build_detection_report(record, store.list_reviews(batch_id))
    report["request_id"] = request_id
    return schemas.DetectionReportResponse.model_validate(report)


@router.put(
    "/report/{batch_id}/reviews/{frame_id}",
    response_model=schemas.ReportReviewResponse,
    responses={
        200: {"model": schemas.ReportReviewResponse},
        401: {"model": schemas.ErrorResponse},
        404: {"model": schemas.ErrorResponse},
    },
)
async def upsert_report_review(
    batch_id: str,
    frame_id: int,
    payload: schemas.ReportReviewRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> schemas.ReportReviewResponse:
    """写入指定批次中某帧的人工复核信息。"""
    _authorize_report_request(request, settings)
    request_id = getattr(request.state, "request_id", None)
    request.app.state.metrics["report_query_requests_total"] += 1
    store = get_report_store(str(settings.report_store_db_path))
    review = store.upsert_review(
        batch_id=batch_id,
        frame_id=frame_id,
        status=payload.status,
        note=payload.note,
        reviewer=payload.reviewer,
    )
    if review is None:
        request.app.state.metrics["report_not_found_total"] += 1
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "REPORT_NOT_FOUND",
                "message": "上报批次不存在",
                "detail": batch_id,
            },
        )

    return schemas.ReportReviewResponse(
        status="updated",
        batch_id=batch_id,
        review=_review_to_response(review),
        request_id=request_id,
    )


@router.get(
    "/report/{batch_id}/export.csv",
    responses={
        200: {"content": {"text/csv": {}}},
        401: {"model": schemas.ErrorResponse},
        404: {"model": schemas.ErrorResponse},
    },
)
async def export_report_csv(
    batch_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Response:
    """导出指定批次的 CSV 报告。"""
    _authorize_report_request(request, settings)
    request.app.state.metrics["report_query_requests_total"] += 1
    store = get_report_store(str(settings.report_store_db_path))
    record = store.get(batch_id)
    if record is None:
        request.app.state.metrics["report_not_found_total"] += 1
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "REPORT_NOT_FOUND",
                "message": "上报批次不存在",
                "detail": batch_id,
            },
        )

    reviews = store.list_reviews(batch_id)
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(
        [
            "batch_id",
            "device_id",
            "frame_id",
            "timestamp",
            "image_name",
            "label",
            "confidence",
            "bbox",
            "review_status",
            "review_note",
            "reviewer",
            "review_updated_at",
        ]
    )

    for result in record.payload.get("results", []):
        frame_id = int(result.get("frame_id", 0))
        review = reviews.get(frame_id)
        detections = result.get("detections", [])
        rows = detections or [{}]
        for detection in rows:
            writer.writerow(
                [
                    record.batch_id,
                    record.device_id,
                    frame_id,
                    result.get("timestamp", 0),
                    result.get("metadata", {}).get("image_name", ""),
                    detection.get("label", ""),
                    detection.get("confidence", ""),
                    detection.get("bbox", ""),
                    review.status if review else "",
                    review.note if review else "",
                    review.reviewer if review else "",
                    review.updated_at if review else "",
                ]
            )

    return Response(
        content=csv_buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{batch_id}.csv"',
        },
    )


@router.get(
    "/reports/batches",
    response_model=schemas.ReportBatchListResponse,
    responses={200: {"model": schemas.ReportBatchListResponse}},
)
async def list_report_batches(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="返回批次数量上限"),
    device_id: str | None = Query(None, description="按设备 ID 过滤"),
    settings: Settings = Depends(get_settings),
) -> schemas.ReportBatchListResponse:
    """列出最近接收的上报批次。"""
    _authorize_report_request(request, settings)
    request_id = getattr(request.state, "request_id", None)
    request.app.state.metrics["report_query_requests_total"] += 1
    store = get_report_store(str(settings.report_store_db_path))
    items = store.list_batches(limit=limit, device_id=device_id)

    return schemas.ReportBatchListResponse(
        status="ok",
        count=len(items),
        items=[
            schemas.ReportBatchSummaryResponse(
                batch_id=item.batch_id,
                device_id=item.device_id,
                report_time=item.report_time,
                result_count=item.result_count,
                total_detections=item.total_detections,
                created_at=item.created_at,
            )
            for item in items
        ],
        request_id=request_id,
    )


@router.get(
    "/reports/devices",
    response_model=schemas.ReportDeviceListResponse,
    responses={200: {"model": schemas.ReportDeviceListResponse}},
)
async def list_report_devices(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="返回设备数量上限"),
    settings: Settings = Depends(get_settings),
) -> schemas.ReportDeviceListResponse:
    """列出最近有上报的设备聚合概览。"""
    _authorize_report_request(request, settings)
    request_id = getattr(request.state, "request_id", None)
    request.app.state.metrics["report_query_requests_total"] += 1
    store = get_report_store(str(settings.report_store_db_path))
    items = store.list_devices(limit=limit)

    return schemas.ReportDeviceListResponse(
        status="ok",
        count=len(items),
        items=[
            schemas.ReportDeviceSummaryResponse(
                device_id=item.device_id,
                batch_count=item.batch_count,
                result_count=item.result_count,
                total_detections=item.total_detections,
                last_report_time=item.last_report_time,
                last_batch_id=item.last_batch_id,
                last_created_at=item.last_created_at,
                site_name=item.site_name,
                display_name=item.display_name,
                note=item.note,
            )
            for item in items
        ],
        request_id=request_id,
    )


@router.get(
    "/reports/alerts/summary",
    response_model=schemas.AlertSummaryResponse,
    responses={200: {"model": schemas.AlertSummaryResponse}},
)
async def get_alert_summary(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> schemas.AlertSummaryResponse:
    """返回最小告警摘要。"""
    _authorize_report_request(request, settings)
    request_id = getattr(request.state, "request_id", None)
    store = get_report_store(str(settings.report_store_db_path))
    devices = store.list_devices(limit=100)
    now = time.time()
    stale_device_count = sum(
        1 for item in devices if now - item.last_report_time > 3600
    )

    task_manager = get_inference_task_manager()
    tasks = task_manager.list_tasks(limit=100)
    failed_task_count = sum(1 for item in tasks if item.status == "failed")
    partial_failed_task_count = sum(
        1 for item in tasks if item.status == "partial_failed"
    )

    return schemas.AlertSummaryResponse(
        status="ok",
        stale_device_count=stale_device_count,
        failed_task_count=failed_task_count,
        partial_failed_task_count=partial_failed_task_count,
        ready_failure_count=int(
            request.app.state.metrics["health_ready_failures_total"]
        ),
        request_id=request_id,
    )


@router.get(
    "/reports/audit-logs",
    response_model=list[schemas.AuditLogResponse],
    responses={200: {"model": list[schemas.AuditLogResponse]}},
)
async def list_audit_logs(
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="返回日志数量上限"),
    actor: str | None = Query(None, description="按操作者过滤"),
    settings: Settings = Depends(get_settings),
) -> list[schemas.AuditLogResponse]:
    """读取最近的审计日志。"""
    _authorize_report_request(request, settings)
    store = get_report_store(str(settings.report_store_db_path))
    logs = store.list_audit_logs(limit=limit, actor=actor)
    return [
        schemas.AuditLogResponse(
            event_type=item.event_type,
            resource_id=item.resource_id,
            actor=item.actor,
            request_id=item.request_id,
            detail_json=item.detail_json,
            created_at=item.created_at,
        )
        for item in logs
    ]


def _authorize_report_request(request: Request, settings: Settings) -> None:
    """在配置 API Key 时校验上报请求。"""
    expected_key = settings.cloud_api_key
    if not expected_key:
        return

    authorization = request.headers.get("authorization", "")
    api_key = request.headers.get("x-api-key", "")
    bearer_prefix = "Bearer "
    bearer_token = (
        authorization.removeprefix(bearer_prefix)
        if authorization.startswith(bearer_prefix)
        else ""
    )
    if compare_digest(api_key, expected_key) or compare_digest(
        bearer_token,
        expected_key,
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "UNAUTHORIZED",
            "message": "未授权上报",
            "detail": "缺少或无效的 API Key",
        },
    )


def _record_to_response(
    record: ReportStoreSaveResult,
    *,
    request_id: str | None,
    reviews: dict[int, ReportFrameReview] | None = None,
) -> schemas.ReportRecordResponse:
    review_map = reviews or {}
    return schemas.ReportRecordResponse(
        status="found",
        batch_id=record.batch_id,
        device_id=record.device_id,
        report_time=record.report_time,
        result_count=record.result_count,
        total_detections=record.total_detections,
        created_at=record.created_at,
        results=[
            schemas.ReportFrameResultResponse(
                frame_id=int(item.get("frame_id", 0)),
                timestamp=float(item.get("timestamp", 0)),
                source_id=str(item.get("source_id", "")),
                detections=[
                    schemas.DetectionBox.model_validate(detection)
                    for detection in item.get("detections", [])
                ],
                inference_time_ms=float(item.get("inference_time_ms", 0.0)),
                metadata=dict(item.get("metadata", {})),
                review=(
                    _review_to_response(review_map[int(item.get("frame_id", 0))])
                    if int(item.get("frame_id", 0)) in review_map
                    else None
                ),
            )
            for item in record.payload.get("results", [])
        ],
        payload=record.payload,
        request_id=request_id,
    )


def _review_to_response(review: ReportFrameReview) -> schemas.ReportFrameReviewResponse:
    return schemas.ReportFrameReviewResponse(
        frame_id=review.frame_id,
        status=review.status,
        note=review.note,
        reviewer=review.reviewer,
        updated_at=review.updated_at,
    )
