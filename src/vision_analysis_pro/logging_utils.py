"""日志工具。"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """输出一行一个 JSON 对象的结构化日志格式。"""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "service": self.service_name,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in STANDARD_LOG_RECORD_FIELDS and not key.startswith("_")
        }
        if extra_fields:
            payload.update(extra_fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(
    service_name: str,
    *,
    level: int | None = None,
    log_format: str = "json",
) -> None:
    """统一配置根日志与常见服务日志的 formatter。"""
    formatter: logging.Formatter
    if log_format == "text":
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = JsonFormatter(service_name)

    root_logger = logging.getLogger()
    if level is not None:
        root_logger.setLevel(level)

    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        named_logger = logging.getLogger(logger_name)
        if level is not None:
            named_logger.setLevel(level)
        for handler in named_logger.handlers:
            handler.setFormatter(formatter)
