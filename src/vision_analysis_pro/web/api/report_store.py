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


@dataclass(frozen=True)
class ReportBatchSummary:
    """上报批次摘要。"""

    batch_id: str
    device_id: str
    report_time: float
    result_count: int
    total_detections: int
    created_at: float


@dataclass(frozen=True)
class ReportDeviceSummary:
    """设备聚合摘要。"""

    device_id: str
    batch_count: int
    result_count: int
    total_detections: int
    last_report_time: float
    last_batch_id: str
    last_created_at: float


@dataclass(frozen=True)
class ReportFrameReview:
    """单帧人工复核信息。"""

    batch_id: str
    frame_id: int
    status: str
    note: str
    reviewer: str
    updated_at: float


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

    def list_batches(
        self,
        *,
        limit: int = 20,
        device_id: str | None = None,
    ) -> list[ReportBatchSummary]:
        """列出最近接收的上报批次。"""
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                if device_id:
                    rows = conn.execute(
                        """
                        SELECT
                            batch_id,
                            device_id,
                            report_time,
                            result_count,
                            total_detections,
                            created_at
                        FROM edge_report_batches
                        WHERE device_id = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                        """,
                        (device_id, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT
                            batch_id,
                            device_id,
                            report_time,
                            result_count,
                            total_detections,
                            created_at
                        FROM edge_report_batches
                        ORDER BY created_at DESC
                        LIMIT ?
                        """,
                        (limit,),
                    ).fetchall()

        return [_row_to_batch_summary(row) for row in rows]

    def list_devices(self, *, limit: int = 20) -> list[ReportDeviceSummary]:
        """按设备聚合最近上报情况。"""
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT
                        b.device_id AS device_id,
                        COUNT(*) AS batch_count,
                        SUM(b.result_count) AS result_count,
                        SUM(b.total_detections) AS total_detections,
                        MAX(b.report_time) AS last_report_time,
                        latest.batch_id AS last_batch_id,
                        latest.created_at AS last_created_at
                    FROM edge_report_batches AS b
                    JOIN edge_report_batches AS latest
                      ON latest.batch_id = (
                          SELECT inner_b.batch_id
                          FROM edge_report_batches AS inner_b
                          WHERE inner_b.device_id = b.device_id
                          ORDER BY inner_b.created_at DESC
                          LIMIT 1
                      )
                    GROUP BY b.device_id
                    ORDER BY latest.created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [_row_to_device_summary(row) for row in rows]

    def list_reviews(self, batch_id: str) -> dict[int, ReportFrameReview]:
        """读取指定批次的人工复核信息。"""
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT
                        batch_id,
                        frame_id,
                        status,
                        note,
                        reviewer,
                        updated_at
                    FROM edge_report_reviews
                    WHERE batch_id = ?
                    ORDER BY frame_id ASC
                    """,
                    (batch_id,),
                ).fetchall()

        return {int(row["frame_id"]): _row_to_frame_review(row) for row in rows}

    def upsert_review(
        self,
        *,
        batch_id: str,
        frame_id: int,
        status: str,
        note: str,
        reviewer: str,
    ) -> ReportFrameReview | None:
        """写入或更新指定批次的单帧复核信息。"""
        updated_at = time.time()

        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                if self._get_row(conn, batch_id) is None:
                    return None

                conn.execute(
                    """
                    INSERT INTO edge_report_reviews (
                        batch_id,
                        frame_id,
                        status,
                        note,
                        reviewer,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(batch_id, frame_id) DO UPDATE SET
                        status = excluded.status,
                        note = excluded.note,
                        reviewer = excluded.reviewer,
                        updated_at = excluded.updated_at
                    """,
                    (batch_id, frame_id, status, note, reviewer, updated_at),
                )
                conn.commit()
                row = conn.execute(
                    """
                    SELECT
                        batch_id,
                        frame_id,
                        status,
                        note,
                        reviewer,
                        updated_at
                    FROM edge_report_reviews
                    WHERE batch_id = ? AND frame_id = ?
                    """,
                    (batch_id, frame_id),
                ).fetchone()

        if row is None:
            return None
        return _row_to_frame_review(row)

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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_report_reviews (
                    batch_id TEXT NOT NULL,
                    frame_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (batch_id, frame_id),
                    FOREIGN KEY (batch_id) REFERENCES edge_report_batches(batch_id)
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


def _row_to_batch_summary(row: sqlite3.Row) -> ReportBatchSummary:
    return ReportBatchSummary(
        batch_id=str(row["batch_id"]),
        device_id=str(row["device_id"]),
        report_time=float(row["report_time"]),
        result_count=int(row["result_count"]),
        total_detections=int(row["total_detections"]),
        created_at=float(row["created_at"]),
    )


def _row_to_device_summary(row: sqlite3.Row) -> ReportDeviceSummary:
    return ReportDeviceSummary(
        device_id=str(row["device_id"]),
        batch_count=int(row["batch_count"]),
        result_count=int(row["result_count"]),
        total_detections=int(row["total_detections"]),
        last_report_time=float(row["last_report_time"]),
        last_batch_id=str(row["last_batch_id"]),
        last_created_at=float(row["last_created_at"]),
    )


def _row_to_frame_review(row: sqlite3.Row) -> ReportFrameReview:
    return ReportFrameReview(
        batch_id=str(row["batch_id"]),
        frame_id=int(row["frame_id"]),
        status=str(row["status"]),
        note=str(row["note"]),
        reviewer=str(row["reviewer"]),
        updated_at=float(row["updated_at"]),
    )


@lru_cache(maxsize=16)
def get_report_store(db_path: str) -> SQLiteReportStore:
    """获取缓存的上报存储实例。"""
    return SQLiteReportStore(db_path)


def clear_report_store_cache() -> None:
    """清理存储实例缓存，便于测试隔离。"""
    get_report_store.cache_clear()
