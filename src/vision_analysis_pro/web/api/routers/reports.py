"""边缘 Agent 上报 API"""

import logging
from secrets import compare_digest

from fastapi import APIRouter, Depends, HTTPException, Request, status

from vision_analysis_pro.settings import Settings, get_settings
from vision_analysis_pro.web.api import schemas
from vision_analysis_pro.web.api.report_store import (
    ReportStoreSaveResult,
    get_report_store,
)

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

    return _record_to_response(record, request_id=request_id)


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
) -> schemas.ReportRecordResponse:
    return schemas.ReportRecordResponse(
        status="found",
        batch_id=record.batch_id,
        device_id=record.device_id,
        report_time=record.report_time,
        result_count=record.result_count,
        total_detections=record.total_detections,
        created_at=record.created_at,
        payload=record.payload,
        request_id=request_id,
    )
