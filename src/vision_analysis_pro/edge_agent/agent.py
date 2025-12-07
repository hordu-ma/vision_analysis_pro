"""边缘推理 Agent 主程序"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class EdgeAgent:
    """边缘设备推理 Agent"""

    def __init__(self, config_path: str | Path) -> None:
        """初始化 Agent

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        logger.info(f"初始化 Edge Agent，配置文件: {self.config_path}")

    def run(self) -> None:
        """启动 Agent 主循环"""
        logger.info("Edge Agent 启动中...")
        # TODO: 实现视频采集→推理→上报循环
        pass

    def stop(self) -> None:
        """停止 Agent"""
        logger.info("Edge Agent 停止中...")
        pass
