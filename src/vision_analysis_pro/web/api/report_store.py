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
    site_name: str = ""
    display_name: str = ""
    note: str = ""


@dataclass(frozen=True)
class ReportDeviceMetadata:
    """设备元数据。"""

    device_id: str
    site_name: str
    display_name: str
    note: str
    updated_at: float


@dataclass(frozen=True)
class AuditLogRecord:
    """最小审计日志记录。"""

    event_type: str
    resource_id: str
    actor: str
    request_id: str
    detail_json: str
    created_at: float


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
        offset: int = 0,
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
                        ORDER BY created_at DESC, batch_id DESC
                        LIMIT ? OFFSET ?
                        """,
                        (device_id, limit, offset),
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
                        ORDER BY created_at DESC, batch_id DESC
                        LIMIT ? OFFSET ?
                        """,
                        (limit, offset),
                    ).fetchall()

        return [_row_to_batch_summary(row) for row in rows]

    def count_batches(self, *, device_id: str | None = None) -> int:
        """返回上报批次总数（与 list_batches 非事务一致，为近似值）。"""
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                if device_id:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM edge_report_batches WHERE device_id = ?",
                        (device_id,),
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM edge_report_batches",
                    ).fetchone()
        return int(row[0]) if row else 0

    def list_devices(self, *, limit: int = 20, offset: int = 0) -> list[ReportDeviceSummary]:
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
                        latest.created_at AS last_created_at,
                        COALESCE(m.site_name, '') AS site_name,
                        COALESCE(m.display_name, '') AS display_name,
                        COALESCE(m.note, '') AS note
                    FROM edge_report_batches AS b
                    JOIN edge_report_batches AS latest
                      ON latest.batch_id = (
                          SELECT inner_b.batch_id
                          FROM edge_report_batches AS inner_b
                          WHERE inner_b.device_id = b.device_id
                          ORDER BY inner_b.created_at DESC
                          LIMIT 1
                      )
                    LEFT JOIN edge_device_metadata AS m
                      ON m.device_id = b.device_id
                    GROUP BY b.device_id
                    ORDER BY latest.created_at DESC, b.device_id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()

        return [_row_to_device_summary(row) for row in rows]

    def count_devices(self) -> int:
        """返回有上报记录的设备总数（与 list_devices 非事务一致，为近似值）。"""
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(DISTINCT device_id) FROM edge_report_batches",
                ).fetchone()
        return int(row[0]) if row else 0

    def upsert_device_metadata(
        self,
        *,
        device_id: str,
        site_name: str,
        display_name: str,
        note: str,
    ) -> ReportDeviceMetadata:
        updated_at = time.time()
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO edge_device_metadata (
                        device_id,
                        site_name,
                        display_name,
                        note,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(device_id) DO UPDATE SET
                        site_name = excluded.site_name,
                        display_name = excluded.display_name,
                        note = excluded.note,
                        updated_at = excluded.updated_at
                    """,
                    (device_id, site_name, display_name, note, updated_at),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM edge_device_metadata WHERE device_id = ?",
                    (device_id,),
                ).fetchone()
        if row is None:
            raise RuntimeError(f"设备元数据保存失败: {device_id}")
        return _row_to_device_metadata(row)

    def get_device_metadata(self, device_id: str) -> ReportDeviceMetadata | None:
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM edge_device_metadata WHERE device_id = ?",
                    (device_id,),
                ).fetchone()
        return _row_to_device_metadata(row) if row else None

    def append_audit_log(
        self,
        *,
        event_type: str,
        resource_id: str,
        actor: str,
        request_id: str,
        detail: dict[str, Any],
    ) -> None:
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO audit_logs (
                        event_type,
                        resource_id,
                        actor,
                        request_id,
                        detail_json,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_type,
                        resource_id,
                        actor,
                        request_id,
                        json.dumps(detail, ensure_ascii=False),
                        time.time(),
                    ),
                )
                conn.commit()

    def list_audit_logs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        actor: str | None = None,
    ) -> list[AuditLogRecord]:
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                if actor:
                    rows = conn.execute(
                        """
                        SELECT event_type, resource_id, actor, request_id, detail_json, created_at
                        FROM audit_logs
                        WHERE actor = ?
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (actor, limit, offset),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT event_type, resource_id, actor, request_id, detail_json, created_at
                        FROM audit_logs
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (limit, offset),
                    ).fetchall()
        return [_row_to_audit_log(row) for row in rows]

    def count_audit_logs(self, *, actor: str | None = None) -> int:
        with self._lock:
            self._ensure_schema()
            with self._connect() as conn:
                if actor:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM audit_logs WHERE actor = ?",
                        (actor,),
                    ).fetchone()
                else:
                    row = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()
        return int(row[0]) if row else 0

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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_device_metadata (
                    device_id TEXT PRIMARY KEY,
                    site_name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    note TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
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
        site_name=str(row["site_name"]),
        display_name=str(row["display_name"]),
        note=str(row["note"]),
    )


def _row_to_device_metadata(row: sqlite3.Row) -> ReportDeviceMetadata:
    return ReportDeviceMetadata(
        device_id=str(row["device_id"]),
        site_name=str(row["site_name"]),
        display_name=str(row["display_name"]),
        note=str(row["note"]),
        updated_at=float(row["updated_at"]),
    )


def _row_to_audit_log(row: sqlite3.Row) -> AuditLogRecord:
    return AuditLogRecord(
        event_type=str(row["event_type"]),
        resource_id=str(row["resource_id"]),
        actor=str(row["actor"]),
        request_id=str(row["request_id"]),
        detail_json=str(row["detail_json"]),
        created_at=float(row["created_at"]),
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
