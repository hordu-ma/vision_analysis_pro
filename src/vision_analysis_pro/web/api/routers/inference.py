"""推理相关 API"""

import base64
import csv
import io
import logging
import time
from types import SimpleNamespace
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response

from vision_analysis_pro.core.preprocessing.visualization import draw_detections
from vision_analysis_pro.settings import Settings, get_settings
from vision_analysis_pro.web.api import schemas
from vision_analysis_pro.web.api.deps import get_inference_engine
from vision_analysis_pro.web.api.inference_tasks import (
    StoredUploadFile,
    get_inference_task_manager,
)

router = APIRouter(prefix="/api/v1/inference", tags=["inference"])
logger = logging.getLogger(__name__)

# 文件校验常量
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}


def _record_inference_metrics(
    metrics: dict[str, Any],
    *,
    inference_time_ms: float,
    input_bytes: int,
    detection_count: int = 0,
    visualized: bool = False,
    success: bool,
) -> None:
    metrics["inference_duration_ms_sum"] += inference_time_ms
    metrics["inference_duration_ms_count"] += 1
    metrics["inference_duration_ms_last"] = inference_time_ms
    metrics["inference_input_bytes_total"] += input_bytes
    if success:
        metrics["inference_success_total"] += 1
        metrics["inference_detections_total"] += detection_count
        if visualized:
            metrics["inference_visualizations_total"] += 1


def _serialize_detections(result: Any) -> list[schemas.DetectionBox]:
    """将推理结果转换为标准结构

    契约：bbox 格式为 [x1, y1, x2, y2]，像素坐标
    为兼容未来接入 YOLO 原生结果，预留兜底分支。
    """
    detections: list[schemas.DetectionBox] = []

    if isinstance(result, list) and result and isinstance(result[0], dict):
        for item in result:
            bbox_data = item.get("bbox") or item.get("box")
            if bbox_data:
                bbox_list = (
                    list(bbox_data)
                    if isinstance(bbox_data, (tuple, list))
                    else bbox_data
                )
                detections.append(
                    schemas.DetectionBox(
                        label=str(item["label"]),
                        confidence=float(item["confidence"]),
                        bbox=bbox_list,
                    )
                )
        return detections

    return detections


async def _read_and_validate_upload(file: UploadFile) -> bytes:
    """读取并校验上传文件。"""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_FILE",
                "message": "上传的文件为空",
                "detail": f"文件名: {file.filename}",
            },
        )

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": "文件大小超过限制",
                "detail": (
                    f"文件大小: {len(file_bytes)} bytes, "
                    f"最大允许: {MAX_FILE_SIZE} bytes"
                ),
            },
        )

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FORMAT",
                "message": "不支持的文件格式",
                "detail": (
                    f"当前格式: {file.content_type}, "
                    f"支持格式: {', '.join(ALLOWED_MIME_TYPES)}"
                ),
            },
        )

    return file_bytes


def _run_inference(
    *,
    request_id: str,
    file: UploadFile,
    file_bytes: bytes,
    settings: Settings,
    engine: Any,
    metrics: dict[str, Any],
    visualize: bool,
) -> schemas.InferenceResponse:
    """执行单文件推理并更新指标。"""
    start_time = time.perf_counter()
    try:
        raw_result = engine.predict(
            file_bytes,
            conf=settings.confidence_threshold,
            iou=settings.iou_threshold,
        )  # type: ignore[arg-type]
        detections = _serialize_detections(raw_result)
    except RuntimeError as e:
        inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        metrics["inference_failures_total"] += 1
        _record_inference_metrics(
            metrics,
            inference_time_ms=inference_time_ms,
            input_bytes=len(file_bytes),
            success=False,
        )
        logger.exception(
            "inference_request_failed",
            extra={
                "request_id": request_id,
                "upload_filename": file.filename,
                "engine": engine.__class__.__name__,
                "input_bytes": len(file_bytes),
                "inference_time_ms": inference_time_ms,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INFERENCE_ERROR",
                "message": "推理失败",
                "detail": str(e),
            },
        ) from e

    visualization_data = None
    if visualize and detections:
        try:
            detection_dicts = [
                {
                    "label": det.label,
                    "confidence": det.confidence,
                    "bbox": det.bbox,
                }
                for det in detections
            ]
            vis_bytes = draw_detections(file_bytes, detection_dicts)
            vis_base64 = base64.b64encode(vis_bytes).decode("utf-8")
            visualization_data = f"data:image/jpeg;base64,{vis_base64}"
        except Exception:
            visualization_data = None

    inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    detection_count = len(detections)
    visualized = visualization_data is not None
    _record_inference_metrics(
        metrics,
        inference_time_ms=inference_time_ms,
        input_bytes=len(file_bytes),
        detection_count=detection_count,
        visualized=visualized,
        success=True,
    )

    logger.info(
        "inference_request_completed",
        extra={
            "request_id": request_id,
            "upload_filename": file.filename,
            "engine": engine.__class__.__name__,
            "detections": detection_count,
            "input_bytes": len(file_bytes),
            "visualized": visualized,
            "inference_time_ms": inference_time_ms,
        },
    )

    return schemas.InferenceResponse(
        filename=file.filename or "unknown",
        detections=detections,
        metadata={
            "engine": engine.__class__.__name__,
            "request_id": request_id,
            "inference_time_ms": inference_time_ms,
            "detection_count": detection_count,
        },
        visualization=visualization_data,
    )


@router.post(
    "/image",
    response_model=schemas.InferenceResponse,
    responses={
        400: {"model": schemas.ErrorResponse},
        500: {"model": schemas.ErrorResponse},
    },
)
async def inference_image(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Any, Depends(get_inference_engine)],
    file: UploadFile = File(...),
    visualize: bool = Query(False, description="是否返回可视化图像"),
) -> schemas.InferenceResponse:
    """图像推理接口"""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "inference_request_received",
        extra={
            "request_id": request_id,
            "upload_filename": file.filename,
            "content_type": file.content_type,
            "visualize": visualize,
        },
    )

    file_bytes = await _read_and_validate_upload(file)

    metrics: dict[str, Any] = request.app.state.metrics
    metrics["inference_requests_total"] += 1
    return _run_inference(
        request_id=request_id,
        file=file,
        file_bytes=file_bytes,
        settings=settings,
        engine=engine,
        metrics=metrics,
        visualize=visualize,
    )


@router.post(
    "/images",
    response_model=schemas.BatchInferenceResponse,
    responses={
        400: {"model": schemas.ErrorResponse},
        500: {"model": schemas.ErrorResponse},
    },
)
async def inference_images(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Any, Depends(get_inference_engine)],
    files: list[UploadFile] = File(...),
    visualize: bool = Query(False, description="是否返回可视化图像"),
) -> schemas.BatchInferenceResponse:
    """批量图像推理接口。"""
    request_id = getattr(request.state, "request_id", "unknown")
    batch_start_time = time.perf_counter()

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_FILE",
                "message": "至少上传一个文件",
                "detail": "files 不能为空",
            },
        )

    metrics: dict[str, Any] = request.app.state.metrics
    results: list[schemas.InferenceResponse] = []

    for file in files:
        logger.info(
            "inference_request_received",
            extra={
                "request_id": request_id,
                "upload_filename": file.filename,
                "content_type": file.content_type,
                "visualize": visualize,
                "batch_mode": True,
            },
        )
        file_bytes = await _read_and_validate_upload(file)
        metrics["inference_requests_total"] += 1
        results.append(
            _run_inference(
                request_id=request_id,
                file=file,
                file_bytes=file_bytes,
                settings=settings,
                engine=engine,
                metrics=metrics,
                visualize=visualize,
            )
        )

    batch_time_ms = round((time.perf_counter() - batch_start_time) * 1000, 2)
    total_detections = sum(len(item.detections) for item in results)
    return schemas.BatchInferenceResponse(
        files=results,
        metadata={
            "request_id": request_id,
            "engine": engine.__class__.__name__,
            "file_count": len(results),
            "total_detections": total_detections,
            "batch_inference_time_ms": batch_time_ms,
        },
    )


@router.post(
    "/images/tasks",
    response_model=schemas.InferenceTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={202: {"model": schemas.InferenceTaskResponse}},
)
async def create_inference_task(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Any, Depends(get_inference_engine)],
    files: list[UploadFile] = File(...),
    visualize: bool = Query(False, description="是否返回可视化图像"),
) -> schemas.InferenceTaskResponse:
    """创建批量图像异步推理任务。"""
    request_id = getattr(request.state, "request_id", "unknown")
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_FILE",
                "message": "至少上传一个文件",
                "detail": "files 不能为空",
            },
        )

    stored_files: list[StoredUploadFile] = []
    for file in files:
        logger.info(
            "inference_request_received",
            extra={
                "request_id": request_id,
                "upload_filename": file.filename,
                "content_type": file.content_type,
                "visualize": visualize,
                "task_mode": True,
            },
        )
        stored_files.append(
            StoredUploadFile(
                filename=file.filename or "unknown",
                content_type=file.content_type,
                file_bytes=await _read_and_validate_upload(file),
            )
        )

    metrics: dict[str, Any] = request.app.state.metrics
    task_manager = get_inference_task_manager()

    def worker(progress_callback: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return _run_batch_task(
            request_id=request_id,
            stored_files=stored_files,
            settings=settings,
            engine=engine,
            metrics=metrics,
            visualize=visualize,
            progress_callback=progress_callback,
        )

    record = task_manager.create_task(
        file_count=len(stored_files),
        input_files=stored_files,
        visualize=visualize,
        metadata={"request_id": request_id},
        worker=worker,
    )
    return _task_record_to_response(record)


def _run_batch_task(
    *,
    request_id: str,
    stored_files: list[StoredUploadFile],
    settings: Settings,
    engine: Any,
    metrics: dict[str, Any],
    visualize: bool,
    progress_callback: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    batch_start_time = time.perf_counter()
    results: list[schemas.InferenceResponse] = []
    for index, stored_file in enumerate(stored_files, start=1):
        metrics["inference_requests_total"] += 1
        upload_file = SimpleNamespace(
            filename=stored_file.filename,
            content_type=stored_file.content_type,
        )
        result = _run_inference(
            request_id=request_id,
            file=upload_file,
            file_bytes=stored_file.file_bytes,
            settings=settings,
            engine=engine,
            metrics=metrics,
            visualize=visualize,
        )
        results.append(result)
        progress_callback(index, len(stored_files))

    batch_time_ms = round((time.perf_counter() - batch_start_time) * 1000, 2)
    total_detections = sum(len(item.detections) for item in results)
    return (
        [item.model_dump(mode="json") for item in results],
        {
            "request_id": request_id,
            "engine": engine.__class__.__name__,
            "file_count": len(results),
            "total_detections": total_detections,
            "batch_inference_time_ms": batch_time_ms,
            "visualize": visualize,
        },
    )


def _create_replayed_task(
    *,
    source_record: Any,
    request_id: str,
    settings: Settings,
    engine: Any,
    metrics: dict[str, Any],
) -> schemas.InferenceTaskResponse:
    task_manager = get_inference_task_manager()
    stored_files = list(source_record.input_files)
    visualize = source_record.visualize

    def worker(progress_callback: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return _run_batch_task(
            request_id=request_id,
            stored_files=stored_files,
            settings=settings,
            engine=engine,
            metrics=metrics,
            visualize=visualize,
            progress_callback=progress_callback,
        )

    record = task_manager.create_task(
        file_count=len(stored_files),
        input_files=stored_files,
        visualize=visualize,
        metadata={
            "request_id": request_id,
            "source_task_id": source_record.task_id,
            "replay_mode": "retry" if source_record.status == "failed" else "rerun",
        },
        worker=worker,
    )
    return _task_record_to_response(record)


@router.get(
    "/images/tasks",
    response_model=list[schemas.InferenceTaskResponse],
    responses={200: {"model": list[schemas.InferenceTaskResponse]}},
)
async def list_inference_tasks(
    limit: int = Query(20, ge=1, le=100, description="返回任务数量上限"),
    status_filter: str | None = Query(
        None,
        alias="status",
        pattern="^(pending|running|completed|failed)$",
        description="按任务状态过滤",
    ),
) -> list[schemas.InferenceTaskResponse]:
    """列出最近的批量推理任务。"""
    task_manager = get_inference_task_manager()
    records = task_manager.list_tasks(limit=limit, status_filter=status_filter)
    return [_task_record_to_response(record) for record in records]


@router.get(
    "/images/tasks/{task_id}",
    response_model=schemas.InferenceTaskResponse,
    responses={
        200: {"model": schemas.InferenceTaskResponse},
        404: {"model": schemas.ErrorResponse},
    },
)
async def get_inference_task(task_id: str) -> schemas.InferenceTaskResponse:
    """查询批量图像异步推理任务。"""
    task_manager = get_inference_task_manager()
    record = task_manager.get_task(task_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TASK_NOT_FOUND",
                "message": "批量推理任务不存在",
                "detail": task_id,
            },
        )
    return _task_record_to_response(record)


@router.post(
    "/images/tasks/{task_id}/retry",
    response_model=schemas.InferenceTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": schemas.InferenceTaskResponse},
        400: {"model": schemas.ErrorResponse},
        404: {"model": schemas.ErrorResponse},
    },
)
async def retry_inference_task(
    task_id: str,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Any, Depends(get_inference_engine)],
) -> schemas.InferenceTaskResponse:
    """重试失败的批量图像异步推理任务。"""
    task_manager = get_inference_task_manager()
    record = task_manager.get_task(task_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TASK_NOT_FOUND",
                "message": "批量推理任务不存在",
                "detail": task_id,
            },
        )
    if record.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TASK_RETRY_NOT_ALLOWED",
                "message": "仅失败任务支持重试",
                "detail": task_id,
            },
        )

    request_id = getattr(request.state, "request_id", "unknown")
    metrics: dict[str, Any] = request.app.state.metrics
    return _create_replayed_task(
        source_record=record,
        request_id=request_id,
        settings=settings,
        engine=engine,
        metrics=metrics,
    )


@router.post(
    "/images/tasks/{task_id}/rerun",
    response_model=schemas.InferenceTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": schemas.InferenceTaskResponse},
        404: {"model": schemas.ErrorResponse},
    },
)
async def rerun_inference_task(
    task_id: str,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Any, Depends(get_inference_engine)],
) -> schemas.InferenceTaskResponse:
    """复跑历史批量图像异步推理任务。"""
    task_manager = get_inference_task_manager()
    record = task_manager.get_task(task_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TASK_NOT_FOUND",
                "message": "批量推理任务不存在",
                "detail": task_id,
            },
        )

    request_id = getattr(request.state, "request_id", "unknown")
    metrics: dict[str, Any] = request.app.state.metrics
    return _create_replayed_task(
        source_record=record,
        request_id=request_id,
        settings=settings,
        engine=engine,
        metrics=metrics,
    )


@router.get(
    "/images/tasks/{task_id}/export.csv",
    responses={
        200: {"content": {"text/csv": {}}},
        400: {"model": schemas.ErrorResponse},
        404: {"model": schemas.ErrorResponse},
    },
)
async def export_inference_task_csv(task_id: str) -> Response:
    """导出已完成批量任务的 CSV 结果。"""
    task_manager = get_inference_task_manager()
    record = task_manager.get_task(task_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TASK_NOT_FOUND",
                "message": "批量推理任务不存在",
                "detail": task_id,
            },
        )
    if record.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TASK_EXPORT_NOT_ALLOWED",
                "message": "仅已完成任务支持导出",
                "detail": task_id,
            },
        )

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(
        [
            "task_id",
            "filename",
            "label",
            "confidence",
            "bbox",
            "detection_count",
            "inference_time_ms",
            "engine",
            "request_id",
        ]
    )

    for result in record.results:
        detections = result.get("detections", [])
        metadata = result.get("metadata", {})
        rows = detections or [{}]
        for detection in rows:
            writer.writerow(
                [
                    task_id,
                    result.get("filename", ""),
                    detection.get("label", ""),
                    detection.get("confidence", ""),
                    detection.get("bbox", ""),
                    metadata.get("detection_count", len(detections)),
                    metadata.get("inference_time_ms", ""),
                    metadata.get("engine", ""),
                    metadata.get("request_id", record.metadata.get("request_id", "")),
                ]
            )

    return Response(
        content=csv_buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{task_id}.csv"',
        },
    )


def _task_record_to_response(record: Any) -> schemas.InferenceTaskResponse:
    return schemas.InferenceTaskResponse(
        task_id=record.task_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        file_count=record.file_count,
        completed_files=record.completed_files,
        progress=record.progress,
        results=[
            schemas.InferenceResponse.model_validate(item) for item in record.results
        ],
        metadata=record.metadata,
        error=record.error,
    )
