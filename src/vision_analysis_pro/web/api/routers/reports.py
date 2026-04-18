"""边缘 Agent 上报 API"""

import logging

from fastapi import APIRouter, Request, status

from vision_analysis_pro.web.api import schemas

router = APIRouter(prefix="/api/v1", tags=["reports"])
logger = logging.getLogger(__name__)


@router.post(
    "/report",
    response_model=schemas.ReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": schemas.ReportResponse},
        422: {"model": schemas.ErrorResponse},
    },
)
async def receive_report(
    request: Request,
    payload: schemas.ReportPayloadRequest,
) -> schemas.ReportResponse:
    """接收边缘 Agent 批量上报结果。

    当前最小实现只确认接收并记录基础指标，后续可在此处接入数据库、
    消息队列或告警规则。
    """
    request_id = getattr(request.state, "request_id", None)
    result_count = len(payload.results)
    total_detections = sum(len(result.detections) for result in payload.results)

    metrics: dict[str, int] = request.app.state.metrics
    metrics["report_requests_total"] += 1
    metrics["report_results_total"] += result_count
    metrics["report_detections_total"] += total_detections

    logger.info(
        "edge_report_received",
        extra={
            "request_id": request_id,
            "device_id": payload.device_id,
            "batch_id": payload.batch_id,
            "result_count": result_count,
            "total_detections": total_detections,
        },
    )

    return schemas.ReportResponse(
        status="accepted",
        message="上报已接收",
        batch_id=payload.batch_id,
        result_count=result_count,
        total_detections=total_detections,
        request_id=request_id,
    )
