"""边缘上报批次持久化存储。"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from vision_analysis_pro.web.api import schemas


@dataclass(frozen=True)
class ReportStoreSaveResult:
    """上报批次保存结果。"""

    created: bool
    batch_id: str
    device_id: str
    report_time: float
    result_count: int
    total_detections: int
    payload: dict[str, Any]
    created_at: float


class SQLiteReportStore:
    """基于 SQLite 的边缘上报批次存储。"""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._ensure_schema()

    def save(
        self,
        payload: schemas.ReportPayloadRequest,
    ) -> ReportStoreSaveResult:
        """保存上报批次；已存在的 batch_id 按幂等重复处理。"""
        payload_data = payload.model_dump(mode="json")
        payload_json = json.dumps(payload_data, ensure_ascii=False)
        result_count = len(payload.results)
        total_detections = sum(len(result.detections) for result in payload.results)
        created_at = time.time()

        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                try:
                    conn.execute(
                        """
                        INSERT INTO edge_report_batches (
                            batch_id,
                            device_id,
                            report_time,
                            result_count,
                            total_detections,
                            payload_json,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            payload.batch_id,
                            payload.device_id,
                            payload.report_time,
                            result_count,
                            total_detections,
                            payload_json,
                            created_at,
                        ),
                    )
                    conn.commit()
                except sqlite3.IntegrityError:
                    existing = self._get_row(conn, payload.batch_id)
                    if existing is None:
                        raise
                    return _row_to_result(existing, created=False)

                existing = self._get_row(conn, payload.batch_id)
                if existing is None:
                    raise RuntimeError(f"上报批次保存后无法读取: {payload.batch_id}")
                return _row_to_result(existing, created=True)

    def get(self, batch_id: str) -> ReportStoreSaveResult | None:
        """读取指定上报批次。"""
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                row = self._get_row(conn, batch_id)

        if row is None:
            return None
        return _row_to_result(row, created=False)

    def _ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_report_batches (
                    batch_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    report_time REAL NOT NULL,
                    result_count INTEGER NOT NULL,
                    total_detections INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _get_row(conn: sqlite3.Connection, batch_id: str) -> sqlite3.Row | None:
        return conn.execute(
            """
            SELECT
                batch_id,
                device_id,
                report_time,
                result_count,
                total_detections,
                payload_json,
                created_at
            FROM edge_report_batches
            WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchone()


def _row_to_result(row: sqlite3.Row, *, created: bool) -> ReportStoreSaveResult:
    return ReportStoreSaveResult(
        created=created,
        batch_id=str(row["batch_id"]),
        device_id=str(row["device_id"]),
        report_time=float(row["report_time"]),
        result_count=int(row["result_count"]),
        total_detections=int(row["total_detections"]),
        payload=json.loads(str(row["payload_json"])),
        created_at=float(row["created_at"]),
    )


@lru_cache(maxsize=16)
def get_report_store(db_path: str) -> SQLiteReportStore:
    """获取缓存的上报存储实例。"""
    return SQLiteReportStore(db_path)


def clear_report_store_cache() -> None:
    """清理存储实例缓存，便于测试隔离。"""
    get_report_store.cache_clear()
