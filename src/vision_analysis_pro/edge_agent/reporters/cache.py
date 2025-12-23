"""离线缓存管理器

使用 SQLite 实现本地缓存，用于网络不可用时暂存上报数据。
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from types import TracebackType

from ..config import CacheConfig
from ..models import CacheEntry, Detection, InferenceResult, ReportPayload

logger = logging.getLogger(__name__)


class CacheManager:
    """离线缓存管理器

    使用 SQLite 数据库存储待上报的数据，支持：
    - 自动创建数据库和表结构
    - 线程安全的读写操作
    - 自动清理过期缓存
    - 最大条目数限制

    Attributes:
        config: 缓存配置
    """

    def __init__(self, config: CacheConfig) -> None:
        """初始化缓存管理器

        Args:
            config: 缓存配置
        """
        self.config = config
        self._db_path = Path(config.db_path)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """缓存是否已打开"""
        return self._is_open

    def open(self) -> None:
        """打开缓存数据库

        如果数据库文件不存在，将自动创建。

        Raises:
            RuntimeError: 无法打开数据库
        """
        if self._is_open:
            return

        try:
            # 确保目录存在
            self._db_path.parent.mkdir(parents=True, exist_ok=True)

            # 连接数据库
            self._conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                isolation_level="IMMEDIATE",
            )
            self._conn.row_factory = sqlite3.Row

            # 创建表结构
            self._create_tables()

            self._is_open = True
            logger.info(f"缓存数据库已打开: {self._db_path}")

        except sqlite3.Error as e:
            raise RuntimeError(f"无法打开缓存数据库: {e}") from e

    def close(self) -> None:
        """关闭缓存数据库"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        self._is_open = False
        logger.info("缓存数据库已关闭")

    def __enter__(self) -> "CacheManager":
        """上下文管理器入口"""
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """上下文管理器出口"""
        self.close()

    def _create_tables(self) -> None:
        """创建数据库表结构"""
        if self._conn is None:
            return

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT UNIQUE NOT NULL,
                    device_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT DEFAULT ''
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON cache_entries(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_id ON cache_entries(device_id)
            """)
            self._conn.commit()

    def add(self, payload: ReportPayload) -> int:
        """添加缓存条目

        Args:
            payload: 上报数据载荷

        Returns:
            缓存条目 ID

        Raises:
            RuntimeError: 缓存未打开或添加失败
        """
        if not self._is_open or self._conn is None:
            raise RuntimeError("缓存未打开")

        # 序列化 payload
        payload_json = json.dumps(payload.to_dict(), ensure_ascii=False)

        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO cache_entries
                    (batch_id, device_id, payload_json, created_at, retry_count, last_error)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.batch_id,
                        payload.device_id,
                        payload_json,
                        datetime.now().timestamp(),
                        payload.retry_count,
                        "",
                    ),
                )
                self._conn.commit()
                entry_id = cursor.lastrowid or 0

                logger.debug(f"缓存条目已添加: {payload.batch_id} (ID: {entry_id})")
                return entry_id

            except sqlite3.Error as e:
                raise RuntimeError(f"添加缓存失败: {e}") from e

    def get(self, entry_id: int) -> CacheEntry | None:
        """获取缓存条目

        Args:
            entry_id: 缓存条目 ID

        Returns:
            CacheEntry 实例，如果不存在则返回 None
        """
        if not self._is_open or self._conn is None:
            return None

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM cache_entries WHERE id = ?",
                (entry_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_entry(row)

    def get_pending(self, limit: int = 100) -> list[CacheEntry]:
        """获取待处理的缓存条目

        按创建时间升序返回（先进先出）。

        Args:
            limit: 最大返回数量

        Returns:
            CacheEntry 列表
        """
        if not self._is_open or self._conn is None:
            return []

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT * FROM cache_entries
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

            return [self._row_to_entry(row) for row in rows]

    def remove(self, entry_id: int) -> bool:
        """移除缓存条目

        Args:
            entry_id: 缓存条目 ID

        Returns:
            是否成功移除
        """
        if not self._is_open or self._conn is None:
            return False

        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    "DELETE FROM cache_entries WHERE id = ?",
                    (entry_id,),
                )
                self._conn.commit()
                removed = cursor.rowcount > 0

                if removed:
                    logger.debug(f"缓存条目已移除: ID {entry_id}")

                return removed

            except sqlite3.Error as e:
                logger.error(f"移除缓存条目失败: {e}")
                return False

    def remove_by_batch_id(self, batch_id: str) -> bool:
        """按批次 ID 移除缓存条目

        Args:
            batch_id: 批次 ID

        Returns:
            是否成功移除
        """
        if not self._is_open or self._conn is None:
            return False

        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    "DELETE FROM cache_entries WHERE batch_id = ?",
                    (batch_id,),
                )
                self._conn.commit()
                return cursor.rowcount > 0

            except sqlite3.Error as e:
                logger.error(f"移除缓存条目失败: {e}")
                return False

    def update_retry(self, entry_id: int, error: str = "") -> None:
        """更新重试计数

        Args:
            entry_id: 缓存条目 ID
            error: 错误信息
        """
        if not self._is_open or self._conn is None:
            return

        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    """
                    UPDATE cache_entries
                    SET retry_count = retry_count + 1, last_error = ?
                    WHERE id = ?
                    """,
                    (error, entry_id),
                )
                self._conn.commit()

            except sqlite3.Error as e:
                logger.error(f"更新重试计数失败: {e}")

    def count(self) -> int:
        """获取缓存条目数量

        Returns:
            缓存条目数量
        """
        if not self._is_open or self._conn is None:
            return 0

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cache_entries")
            row = cursor.fetchone()
            return row[0] if row else 0

    def clear(self) -> int:
        """清空所有缓存

        Returns:
            清除的条目数量
        """
        if not self._is_open or self._conn is None:
            return 0

        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM cache_entries")
                count = cursor.fetchone()[0]

                cursor.execute("DELETE FROM cache_entries")
                self._conn.commit()

                logger.info(f"已清空 {count} 个缓存条目")
                return count

            except sqlite3.Error as e:
                logger.error(f"清空缓存失败: {e}")
                return 0

    def cleanup_expired(self) -> int:
        """清理过期缓存

        根据配置的 max_age_hours 清理过期条目。

        Returns:
            清除的条目数量
        """
        if not self._is_open or self._conn is None:
            return 0

        max_age_seconds = self.config.max_age_hours * 3600
        cutoff_time = datetime.now().timestamp() - max_age_seconds

        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    "DELETE FROM cache_entries WHERE created_at < ?",
                    (cutoff_time,),
                )
                self._conn.commit()
                removed = cursor.rowcount

                if removed > 0:
                    logger.info(f"已清理 {removed} 个过期缓存条目")

                return removed

            except sqlite3.Error as e:
                logger.error(f"清理过期缓存失败: {e}")
                return 0

    def cleanup_overflow(self) -> int:
        """清理超出最大条目数的缓存

        保留最新的条目，删除最旧的。

        Returns:
            清除的条目数量
        """
        if not self._is_open or self._conn is None:
            return 0

        current_count = self.count()
        if current_count <= self.config.max_entries:
            return 0

        to_remove = current_count - self.config.max_entries

        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM cache_entries
                    WHERE id IN (
                        SELECT id FROM cache_entries
                        ORDER BY created_at ASC
                        LIMIT ?
                    )
                    """,
                    (to_remove,),
                )
                self._conn.commit()
                removed = cursor.rowcount

                if removed > 0:
                    logger.info(f"已清理 {removed} 个溢出缓存条目")

                return removed

            except sqlite3.Error as e:
                logger.error(f"清理溢出缓存失败: {e}")
                return 0

    def cleanup(self) -> int:
        """执行完整清理

        清理过期和溢出的缓存条目。

        Returns:
            总共清除的条目数量
        """
        expired = self.cleanup_expired()
        overflow = self.cleanup_overflow()
        return expired + overflow

    def get_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            包含统计信息的字典
        """
        if not self._is_open or self._conn is None:
            return {
                "is_open": False,
                "count": 0,
            }

        with self._lock:
            cursor = self._conn.cursor()

            # 总数
            cursor.execute("SELECT COUNT(*) FROM cache_entries")
            count = cursor.fetchone()[0]

            # 最早条目时间
            cursor.execute("SELECT MIN(created_at) FROM cache_entries")
            oldest = cursor.fetchone()[0]

            # 最新条目时间
            cursor.execute("SELECT MAX(created_at) FROM cache_entries")
            newest = cursor.fetchone()[0]

            # 平均重试次数
            cursor.execute("SELECT AVG(retry_count) FROM cache_entries")
            avg_retry = cursor.fetchone()[0] or 0

            return {
                "is_open": True,
                "db_path": str(self._db_path),
                "count": count,
                "max_entries": self.config.max_entries,
                "max_age_hours": self.config.max_age_hours,
                "oldest_entry": oldest,
                "newest_entry": newest,
                "avg_retry_count": round(avg_retry, 2),
            }

    def _row_to_entry(self, row: sqlite3.Row) -> CacheEntry:
        """将数据库行转换为 CacheEntry

        Args:
            row: 数据库行

        Returns:
            CacheEntry 实例
        """
        payload_data = json.loads(row["payload_json"])

        # 重建 ReportPayload
        results = [
            InferenceResult(
                frame_id=r["frame_id"],
                timestamp=r["timestamp"],
                source_id=r["source_id"],
                detections=[Detection.from_dict(d) for d in r["detections"]],
                inference_time_ms=r.get("inference_time_ms", 0.0),
                metadata=r.get("metadata", {}),
            )
            for r in payload_data["results"]
        ]

        payload = ReportPayload(
            device_id=payload_data["device_id"],
            results=results,
            report_time=payload_data["report_time"],
            batch_id=payload_data["batch_id"],
        )

        return CacheEntry(
            id=row["id"],
            payload=payload,
            created_at=row["created_at"],
            retry_count=row["retry_count"],
            last_error=row["last_error"],
        )
