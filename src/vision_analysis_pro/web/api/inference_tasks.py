"""批量推理异步任务管理。"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InferenceTaskRecord:
    """批量推理任务记录。"""

    task_id: str
    status: str
    created_at: float
    updated_at: float
    file_count: int
    progress: int = 0
    completed_files: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, str] | None = None


class InferenceTaskManager:
    """基于内存线程的最小批量推理任务管理器。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: dict[str, InferenceTaskRecord] = {}

    def create_task(
        self,
        *,
        file_count: int,
        worker: Callable[
            [Callable[[int, int], None]], tuple[list[dict[str, Any]], dict[str, Any]]
        ],
    ) -> InferenceTaskRecord:
        task_id = f"task-{uuid.uuid4().hex}"
        now = time.time()
        record = InferenceTaskRecord(
            task_id=task_id,
            status="pending",
            created_at=now,
            updated_at=now,
            file_count=file_count,
        )
        with self._lock:
            self._tasks[task_id] = record

        thread = threading.Thread(
            target=self._run_task,
            args=(task_id, worker),
            daemon=True,
            name=f"inference-task-{task_id}",
        )
        thread.start()
        return self.get_task(task_id) or record

    def get_task(self, task_id: str) -> InferenceTaskRecord | None:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                return None
            return InferenceTaskRecord(
                task_id=record.task_id,
                status=record.status,
                created_at=record.created_at,
                updated_at=record.updated_at,
                file_count=record.file_count,
                progress=record.progress,
                completed_files=record.completed_files,
                results=list(record.results),
                metadata=dict(record.metadata),
                error=dict(record.error) if record.error else None,
            )

    def list_tasks(self, *, limit: int = 20) -> list[InferenceTaskRecord]:
        with self._lock:
            records = sorted(
                self._tasks.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )[:limit]

        return [
            InferenceTaskRecord(
                task_id=record.task_id,
                status=record.status,
                created_at=record.created_at,
                updated_at=record.updated_at,
                file_count=record.file_count,
                progress=record.progress,
                completed_files=record.completed_files,
                results=list(record.results),
                metadata=dict(record.metadata),
                error=dict(record.error) if record.error else None,
            )
            for record in records
        ]

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()

    def _run_task(
        self,
        task_id: str,
        worker: Callable[
            [Callable[[int, int], None]], tuple[list[dict[str, Any]], dict[str, Any]]
        ],
    ) -> None:
        self._update_task(task_id, status="running")

        def progress_callback(completed_files: int, total_files: int) -> None:
            progress = int((completed_files / total_files) * 100) if total_files else 0
            self._update_task(
                task_id,
                completed_files=completed_files,
                progress=progress,
            )

        try:
            results, metadata = worker(progress_callback)
        except Exception as exc:
            self._update_task(
                task_id,
                status="failed",
                error={
                    "code": "INFERENCE_TASK_FAILED",
                    "message": "批量任务执行失败",
                    "detail": str(exc),
                },
            )
            return

        self._update_task(
            task_id,
            status="completed",
            completed_files=len(results),
            progress=100,
            results=results,
            metadata=metadata,
        )

    def _update_task(self, task_id: str, **updates: Any) -> None:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                return
            for key, value in updates.items():
                setattr(record, key, value)
            record.updated_at = time.time()


_task_manager = InferenceTaskManager()


def get_inference_task_manager() -> InferenceTaskManager:
    return _task_manager


def clear_inference_task_manager() -> None:
    _task_manager.clear()
