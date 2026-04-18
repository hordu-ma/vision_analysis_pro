"""Pytest 全局测试配置。"""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """在 pytest 启动时显式注册自定义 markers。"""
    config.addinivalue_line(
        "markers",
        "unit: 纯单元测试，不依赖真实模型或外部服务",
    )
    config.addinivalue_line(
        "markers",
        "integration: 集成测试，覆盖模块间协作",
    )
    config.addinivalue_line(
        "markers",
        "model: 依赖真实模型文件的测试",
    )
    config.addinivalue_line(
        "markers",
        "e2e: 端到端测试，覆盖完整请求链路",
    )
