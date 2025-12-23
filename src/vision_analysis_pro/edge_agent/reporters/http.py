"""HTTP 上报器

使用 HTTP/HTTPS 协议上报推理结果，支持：
- 指数退避重试
- 离线缓存
- 批量上报
"""

import asyncio
import logging
import time

import httpx

from ..config import CacheConfig, ReporterConfig
from ..models import ReportPayload, ReportStatus
from .base import BaseReporter
from .cache import CacheManager

logger = logging.getLogger(__name__)


class HTTPReporter(BaseReporter):
    """HTTP 上报器

    通过 HTTP/HTTPS 协议将推理结果上报到云端服务器。
    支持自动重试、离线缓存和批量上报。

    Attributes:
        config: 上报器配置
        cache_config: 缓存配置（可选）
    """

    def __init__(
        self,
        config: ReporterConfig,
        cache_config: CacheConfig | None = None,
    ) -> None:
        """初始化 HTTP 上报器

        Args:
            config: 上报器配置
            cache_config: 缓存配置，为 None 则禁用缓存
        """
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None
        self._sync_client: httpx.Client | None = None
        self._cache: CacheManager | None = None

        if cache_config and cache_config.enabled:
            self._cache = CacheManager(cache_config)

    @property
    def has_cache(self) -> bool:
        """是否启用缓存"""
        return self._cache is not None

    def connect(self) -> None:
        """建立连接

        初始化 HTTP 客户端和缓存管理器。

        Raises:
            ConnectionError: 连接失败
        """
        if self._is_connected:
            return

        try:
            # 配置 HTTP 客户端
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "EdgeAgent/1.0",
            }

            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"

            timeout = httpx.Timeout(
                timeout=self.config.timeout,
                connect=10.0,
            )

            # 创建异步客户端
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
            )

            # 创建同步客户端
            self._sync_client = httpx.Client(
                headers=headers,
                timeout=timeout,
            )

            # 打开缓存
            if self._cache:
                self._cache.open()

            self._is_connected = True
            logger.info(f"HTTP 上报器已连接: {self.config.url}")

        except Exception as e:
            raise ConnectionError(f"HTTP 上报器连接失败: {e}") from e

    def disconnect(self) -> None:
        """断开连接，释放资源"""
        if self._client:
            # 在事件循环中关闭异步客户端
            try:
                asyncio.get_event_loop().run_until_complete(self._client.aclose())
            except RuntimeError:
                # 没有运行的事件循环，创建新的
                asyncio.run(self._client.aclose())
            self._client = None

        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

        if self._cache:
            self._cache.close()

        self._is_connected = False
        logger.info("HTTP 上报器已断开")

    async def report(self, payload: ReportPayload) -> ReportStatus:
        """异步上报数据

        Args:
            payload: 上报数据载荷

        Returns:
            上报状态
        """
        if not self._is_connected or self._client is None:
            logger.error("HTTP 上报器未连接")
            self._record_result(success=False)
            return ReportStatus.FAILED

        # 尝试上报（带重试）
        status = await self._send_with_retry(payload)

        # 如果失败且有缓存，加入缓存
        if status == ReportStatus.FAILED and self._cache:
            try:
                self._cache.add(payload)
                logger.info(f"上报失败，已缓存: {payload.batch_id}")
                return ReportStatus.CACHED
            except Exception as e:
                logger.error(f"缓存失败: {e}")

        return status

    def report_sync(self, payload: ReportPayload) -> ReportStatus:
        """同步上报数据

        Args:
            payload: 上报数据载荷

        Returns:
            上报状态
        """
        if not self._is_connected or self._sync_client is None:
            logger.error("HTTP 上报器未连接")
            self._record_result(success=False)
            return ReportStatus.FAILED

        # 尝试上报（带重试）
        status = self._send_with_retry_sync(payload)

        # 如果失败且有缓存，加入缓存
        if status == ReportStatus.FAILED and self._cache:
            try:
                self._cache.add(payload)
                logger.info(f"上报失败，已缓存: {payload.batch_id}")
                return ReportStatus.CACHED
            except Exception as e:
                logger.error(f"缓存失败: {e}")

        return status

    async def _send_with_retry(self, payload: ReportPayload) -> ReportStatus:
        """带重试的异步发送

        使用指数退避策略进行重试。

        Args:
            payload: 上报数据载荷

        Returns:
            上报状态
        """
        if self._client is None:
            return ReportStatus.FAILED

        delay = self.config.retry_delay

        for attempt in range(self.config.retry_max + 1):
            try:
                response = await self._client.post(
                    str(self.config.url),
                    json=payload.to_dict(),
                )

                if response.is_success:
                    self._record_result(success=True)
                    logger.debug(
                        f"上报成功: {payload.batch_id} "
                        f"(尝试 {attempt + 1}/{self.config.retry_max + 1})"
                    )
                    return ReportStatus.SUCCESS

                # 服务器返回错误
                if response.status_code >= 400 and response.status_code < 500:
                    # 客户端错误，不重试
                    logger.error(
                        f"上报失败 (客户端错误): {response.status_code} - "
                        f"{response.text[:200]}"
                    )
                    self._record_result(success=False)
                    return ReportStatus.FAILED

                # 服务器错误，继续重试
                logger.warning(
                    f"上报失败 (服务器错误): {response.status_code} "
                    f"(尝试 {attempt + 1}/{self.config.retry_max + 1})"
                )

            except httpx.TimeoutException:
                logger.warning(
                    f"上报超时 (尝试 {attempt + 1}/{self.config.retry_max + 1})"
                )

            except httpx.ConnectError as e:
                logger.warning(
                    f"连接失败: {e} (尝试 {attempt + 1}/{self.config.retry_max + 1})"
                )

            except httpx.HTTPError as e:
                logger.warning(
                    f"HTTP 错误: {e} (尝试 {attempt + 1}/{self.config.retry_max + 1})"
                )

            # 如果还有重试机会，等待后重试
            if attempt < self.config.retry_max:
                await asyncio.sleep(delay)
                delay *= self.config.retry_backoff  # 指数退避

        self._record_result(success=False)
        logger.error(f"上报失败，已达到最大重试次数: {payload.batch_id}")
        return ReportStatus.FAILED

    def _send_with_retry_sync(self, payload: ReportPayload) -> ReportStatus:
        """带重试的同步发送

        使用指数退避策略进行重试。

        Args:
            payload: 上报数据载荷

        Returns:
            上报状态
        """
        if self._sync_client is None:
            return ReportStatus.FAILED

        delay = self.config.retry_delay

        for attempt in range(self.config.retry_max + 1):
            try:
                response = self._sync_client.post(
                    str(self.config.url),
                    json=payload.to_dict(),
                )

                if response.is_success:
                    self._record_result(success=True)
                    logger.debug(
                        f"上报成功: {payload.batch_id} "
                        f"(尝试 {attempt + 1}/{self.config.retry_max + 1})"
                    )
                    return ReportStatus.SUCCESS

                # 服务器返回错误
                if response.status_code >= 400 and response.status_code < 500:
                    # 客户端错误，不重试
                    logger.error(
                        f"上报失败 (客户端错误): {response.status_code} - "
                        f"{response.text[:200]}"
                    )
                    self._record_result(success=False)
                    return ReportStatus.FAILED

                # 服务器错误，继续重试
                logger.warning(
                    f"上报失败 (服务器错误): {response.status_code} "
                    f"(尝试 {attempt + 1}/{self.config.retry_max + 1})"
                )

            except httpx.TimeoutException:
                logger.warning(
                    f"上报超时 (尝试 {attempt + 1}/{self.config.retry_max + 1})"
                )

            except httpx.ConnectError as e:
                logger.warning(
                    f"连接失败: {e} (尝试 {attempt + 1}/{self.config.retry_max + 1})"
                )

            except httpx.HTTPError as e:
                logger.warning(
                    f"HTTP 错误: {e} (尝试 {attempt + 1}/{self.config.retry_max + 1})"
                )

            # 如果还有重试机会，等待后重试
            if attempt < self.config.retry_max:
                time.sleep(delay)
                delay *= self.config.retry_backoff  # 指数退避

        self._record_result(success=False)
        logger.error(f"上报失败，已达到最大重试次数: {payload.batch_id}")
        return ReportStatus.FAILED

    async def flush_cache(self) -> int:
        """异步刷新缓存

        尝试上报缓存中的数据。

        Returns:
            成功上报的条目数
        """
        if not self._cache or not self._cache.is_open:
            return 0

        entries = self._cache.get_pending(limit=self.config.batch_size)
        if not entries:
            return 0

        success_count = 0
        for entry in entries:
            status = await self._send_with_retry(entry.payload)

            if status == ReportStatus.SUCCESS:
                self._cache.remove(entry.id)
                success_count += 1
            else:
                # 更新重试计数
                self._cache.update_retry(entry.id, f"Retry failed at {time.time()}")

                # 如果重试次数过多，可能需要放弃
                if entry.retry_count >= self.config.retry_max * 3:
                    logger.warning(
                        f"缓存条目重试次数过多，放弃: {entry.payload.batch_id}"
                    )
                    self._cache.remove(entry.id)

        if success_count > 0:
            logger.info(f"缓存刷新完成: {success_count}/{len(entries)} 成功")

        return success_count

    def flush_cache_sync(self) -> int:
        """同步刷新缓存

        尝试上报缓存中的数据。

        Returns:
            成功上报的条目数
        """
        if not self._cache or not self._cache.is_open:
            return 0

        entries = self._cache.get_pending(limit=self.config.batch_size)
        if not entries:
            return 0

        success_count = 0
        for entry in entries:
            status = self._send_with_retry_sync(entry.payload)

            if status == ReportStatus.SUCCESS:
                self._cache.remove(entry.id)
                success_count += 1
            else:
                # 更新重试计数
                self._cache.update_retry(entry.id, f"Retry failed at {time.time()}")

                # 如果重试次数过多，可能需要放弃
                if entry.retry_count >= self.config.retry_max * 3:
                    logger.warning(
                        f"缓存条目重试次数过多，放弃: {entry.payload.batch_id}"
                    )
                    self._cache.remove(entry.id)

        if success_count > 0:
            logger.info(f"缓存刷新完成: {success_count}/{len(entries)} 成功")

        return success_count

    def cleanup_cache(self) -> int:
        """清理缓存

        清理过期和溢出的缓存条目。

        Returns:
            清理的条目数
        """
        if not self._cache or not self._cache.is_open:
            return 0

        return self._cache.cleanup()

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            缓存统计信息字典
        """
        if not self._cache:
            return {"enabled": False}

        stats = self._cache.get_stats()
        stats["enabled"] = True
        return stats

    def get_info(self) -> dict:
        """获取上报器信息"""
        info = super().get_info()
        info["cache"] = self.get_cache_stats()
        return info

    async def health_check(self) -> bool:
        """健康检查

        尝试连接服务器验证可用性。

        Returns:
            服务器是否可用
        """
        if not self._client:
            return False

        try:
            # 尝试 HEAD 请求或 GET 到健康检查端点
            # 假设服务器有 /health 端点
            base_url = str(self.config.url)
            if base_url.endswith("/report"):
                health_url = base_url.replace("/report", "/health")
            else:
                health_url = base_url.rstrip("/") + "/health"

            response = await self._client.get(health_url)
            return response.is_success

        except httpx.HTTPError:
            return False

    def health_check_sync(self) -> bool:
        """同步健康检查

        Returns:
            服务器是否可用
        """
        if not self._sync_client:
            return False

        try:
            base_url = str(self.config.url)
            if base_url.endswith("/report"):
                health_url = base_url.replace("/report", "/health")
            else:
                health_url = base_url.rstrip("/") + "/health"

            response = self._sync_client.get(health_url)
            return response.is_success

        except httpx.HTTPError:
            return False
