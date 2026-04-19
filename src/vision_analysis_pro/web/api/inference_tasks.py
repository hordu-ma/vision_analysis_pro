"""批量推理异步任务管理。"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TERMINAL_TASK_STATUSES = {"completed", "failed"}
MAX_TERMINAL_TASKS = 50


@dataclass
class StoredUploadFile:
    """任务输入文件快照。"""

    filename: str
    content_type: str | None
    file_bytes: bytes


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
    input_files: list[StoredUploadFile] = field(default_factory=list)
    visualize: bool = False


WorkerCallback = Callable[
    [Callable[[int, int], None]], tuple[list[dict[str, Any]], dict[str, Any]]
]


class SQLiteInferenceTaskStore:
    """基于 SQLite 的任务持久化存储。"""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._ensure_schema()

    def save_task(self, record: InferenceTaskRecord) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO inference_tasks (
                    task_id,
                    status,
                    created_at,
                    updated_at,
                    file_count,
                    progress,
                    completed_files,
                    results_json,
                    metadata_json,
                    error_json,
                    input_files_json,
                    visualize
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _record_to_db_tuple(record),
            )
            conn.commit()

    def get_task(self, task_id: str) -> InferenceTaskRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM inference_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return _row_to_record(row) if row else None

    def list_tasks(
        self, *, limit: int = 20, status_filter: str | None = None
    ) -> list[InferenceTaskRecord]:
        query = "SELECT * FROM inference_tasks"
        params: tuple[Any, ...]
        if status_filter is not None:
            query += " WHERE status = ?"
            params = (status_filter, limit)
            query += " ORDER BY created_at DESC LIMIT ?"
        else:
            query += " ORDER BY created_at DESC LIMIT ?"
            params = (limit,)

        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_record(row) for row in rows]

    def delete_task(self, task_id: str) -> bool:
        with self._lock, self._connect() as conn:
            result = conn.execute(
                "DELETE FROM inference_tasks WHERE task_id = ?",
                (task_id,),
            )
            conn.commit()
        return result.rowcount > 0

    def cleanup_tasks(self, *, status_filter: str | None = None) -> int:
        if status_filter is None:
            query = (
                "DELETE FROM inference_tasks WHERE status IN ('completed', 'failed')"
            )
            params: tuple[Any, ...] = ()
        else:
            query = "DELETE FROM inference_tasks WHERE status = ?"
            params = (status_filter,)

        with self._lock, self._connect() as conn:
            result = conn.execute(query, params)
            conn.commit()
        return result.rowcount

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM inference_tasks")
            conn.commit()

    def prune_terminal_tasks(self, *, limit: int = MAX_TERMINAL_TASKS) -> None:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT task_id FROM inference_tasks
                WHERE status IN ('completed', 'failed')
                ORDER BY updated_at DESC
                LIMIT -1 OFFSET ?
                """,
                (limit,),
            ).fetchall()
            if rows:
                conn.executemany(
                    "DELETE FROM inference_tasks WHERE task_id = ?",
                    [(str(row["task_id"]),) for row in rows],
                )
                conn.commit()

    def _ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inference_tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    file_count INTEGER NOT NULL,
                    progress INTEGER NOT NULL,
                    completed_files INTEGER NOT NULL,
                    results_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    error_json TEXT,
                    input_files_json TEXT NOT NULL,
                    visualize INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


class InferenceTaskManager:
    """基于 SQLite 与单 worker 队列的任务管理器。"""

    def __init__(self, db_path: str | Path) -> None:
        self._store = SQLiteInferenceTaskStore(db_path)
        self._lock = threading.Lock()
        self._queue: deque[tuple[str, WorkerCallback]] = deque()
        self._queue_event = threading.Event()
        self._closed = False
        self._worker = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="inference-task-worker",
        )
        self._worker.start()

    def create_task(
        self,
        *,
        file_count: int,
        input_files: list[StoredUploadFile],
        visualize: bool,
        metadata: dict[str, Any] | None = None,
        worker: WorkerCallback,
    ) -> InferenceTaskRecord:
        task_id = f"task-{uuid.uuid4().hex}"
        now = time.time()
        record = InferenceTaskRecord(
            task_id=task_id,
            status="pending",
            created_at=now,
            updated_at=now,
            file_count=file_count,
            metadata=dict(metadata or {}),
            input_files=list(input_files),
            visualize=visualize,
        )
        self._store.save_task(record)
        self._store.prune_terminal_tasks()
        with self._lock:
            self._queue.append((task_id, worker))
            self._queue_event.set()
        return self.get_task(task_id) or record

    def get_task(self, task_id: str) -> InferenceTaskRecord | None:
        return self._store.get_task(task_id)

    def list_tasks(
        self, *, limit: int = 20, status_filter: str | None = None
    ) -> list[InferenceTaskRecord]:
        return self._store.list_tasks(limit=limit, status_filter=status_filter)

    def clear(self) -> None:
        with self._lock:
            self._queue.clear()
        self._store.clear()

    def delete_task(self, task_id: str) -> bool:
        return self._store.delete_task(task_id)

    def cleanup_tasks(self, *, status_filter: str | None = None) -> int:
        return self._store.cleanup_tasks(status_filter=status_filter)

    def _worker_loop(self) -> None:
        while not self._closed:
            self._queue_event.wait()
            while True:
                with self._lock:
                    if not self._queue:
                        self._queue_event.clear()
                        break
                    task_id, worker = self._queue.popleft()
                self._run_task(task_id, worker)

    def _run_task(self, task_id: str, worker: WorkerCallback) -> None:
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

        record = self.get_task(task_id)
        merged_metadata = dict(record.metadata) if record else {}
        merged_metadata.update(metadata)
        task_status = str(merged_metadata.get("status", "completed"))
        task_error = None
        if task_status == "failed":
            task_error = {
                "code": "INFERENCE_TASK_FAILED",
                "message": "批量任务执行失败",
                "detail": "任务中所有文件均执行失败",
            }
        self._update_task(
            task_id,
            status=task_status,
            completed_files=len(results),
            progress=100,
            results=results,
            metadata=merged_metadata,
            error=task_error,
        )

    def _update_task(self, task_id: str, **updates: Any) -> None:
        record = self.get_task(task_id)
        if record is None:
            return
        for key, value in updates.items():
            setattr(record, key, value)
        record.updated_at = time.time()
        self._store.save_task(record)
        self._store.prune_terminal_tasks()


def _record_to_db_tuple(record: InferenceTaskRecord) -> tuple[Any, ...]:
    input_files = [
        {
            "filename": item.filename,
            "content_type": item.content_type,
            "file_bytes": item.file_bytes.hex(),
        }
        for item in record.input_files
    ]
    return (
        record.task_id,
        record.status,
        record.created_at,
        record.updated_at,
        record.file_count,
        record.progress,
        record.completed_files,
        json.dumps(record.results, ensure_ascii=False),
        json.dumps(record.metadata, ensure_ascii=False),
        json.dumps(record.error, ensure_ascii=False) if record.error else None,
        json.dumps(input_files, ensure_ascii=False),
        1 if record.visualize else 0,
    )


def _row_to_record(row: sqlite3.Row) -> InferenceTaskRecord:
    input_files = [
        StoredUploadFile(
            filename=str(item.get("filename", "unknown")),
            content_type=item.get("content_type"),
            file_bytes=bytes.fromhex(str(item.get("file_bytes", ""))),
        )
        for item in json.loads(str(row["input_files_json"]))
    ]
    error_json = row["error_json"]
    return InferenceTaskRecord(
        task_id=str(row["task_id"]),
        status=str(row["status"]),
        created_at=float(row["created_at"]),
        updated_at=float(row["updated_at"]),
        file_count=int(row["file_count"]),
        progress=int(row["progress"]),
        completed_files=int(row["completed_files"]),
        results=list(json.loads(str(row["results_json"]))),
        metadata=dict(json.loads(str(row["metadata_json"]))),
        error=dict(json.loads(str(error_json))) if error_json else None,
        input_files=input_files,
        visualize=bool(row["visualize"]),
    )


_task_manager = InferenceTaskManager(Path("data/inference_tasks.db"))


def get_inference_task_manager() -> InferenceTaskManager:
    return _task_manager


def clear_inference_task_manager() -> None:
    _task_manager.clear()
