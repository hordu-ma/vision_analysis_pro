"""上报器抽象基类

定义结果上报的统一接口，支持 HTTP、MQTT 等多种上报方式。
"""

import logging
from abc import ABC, abstractmethod
from types import TracebackType

from ..config import ReporterConfig
from ..models import ReportPayload, ReportStatus

logger = logging.getLogger(__name__)


class BaseReporter(ABC):
    """上报器抽象基类

    所有上报器实现都应继承此类，并实现相应的抽象方法。
    支持上下文管理器协议，确保资源正确释放。
    """

    def __init__(self, config: ReporterConfig) -> None:
        """初始化上报器

        Args:
            config: 上报器配置
        """
        self.config = config
        self._is_connected = False
        self._report_count = 0
        self._success_count = 0
        self._failure_count = 0

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected

    @property
    def report_count(self) -> int:
        """总上报次数"""
        return self._report_count

    @property
    def success_count(self) -> int:
        """成功上报次数"""
        return self._success_count

    @property
    def failure_count(self) -> int:
        """失败上报次数"""
        return self._failure_count

    @property
    def success_rate(self) -> float:
        """上报成功率"""
        if self._report_count == 0:
            return 0.0
        return self._success_count / self._report_count

    @abstractmethod
    def connect(self) -> None:
        """建立连接

        Raises:
            ConnectionError: 连接失败
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接，释放资源"""
        pass

    @abstractmethod
    async def report(self, payload: ReportPayload) -> ReportStatus:
        """上报数据

        Args:
            payload: 上报数据载荷

        Returns:
            上报状态
        """
        pass

    def report_sync(self, payload: ReportPayload) -> ReportStatus:
        """同步上报数据（阻塞）

        默认实现使用 asyncio.run 包装异步方法。
        子类可以覆盖此方法提供更高效的同步实现。

        Args:
            payload: 上报数据载荷

        Returns:
            上报状态
        """
        import asyncio

        return asyncio.run(self.report(payload))

    def __enter__(self) -> "BaseReporter":
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """上下文管理器出口"""
        self.disconnect()

    def _record_result(self, success: bool) -> None:
        """记录上报结果

        Args:
            success: 是否成功
        """
        self._report_count += 1
        if success:
            self._success_count += 1
        else:
            self._failure_count += 1

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._report_count = 0
        self._success_count = 0
        self._failure_count = 0

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            包含统计信息的字典
        """
        return {
            "report_count": self._report_count,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": self.success_rate,
            "is_connected": self._is_connected,
        }

    def get_info(self) -> dict:
        """获取上报器信息

        Returns:
            包含上报器元信息的字典
        """
        return {
            "type": self.config.type,
            "url": self.config.url,
            "timeout": self.config.timeout,
            "retry_max": self.config.retry_max,
            "batch_size": self.config.batch_size,
            **self.get_stats(),
        }
