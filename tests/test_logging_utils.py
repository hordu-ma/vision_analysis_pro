"""日志工具测试。"""

import json
import logging

from vision_analysis_pro.logging_utils import JsonFormatter


def test_json_formatter_includes_extra_fields() -> None:
    """测试结构化日志包含标准字段和 extra 字段。"""
    formatter = JsonFormatter("vision_api")
    record = logging.LogRecord(
        name="vision_analysis_pro.web.api.main",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"
    record.path = "/api/v1/health"
    record.status_code = 200

    payload = json.loads(formatter.format(record))

    assert payload["service"] == "vision_api"
    assert payload["message"] == "request_completed"
    assert payload["request_id"] == "req-123"
    assert payload["path"] == "/api/v1/health"
    assert payload["status_code"] == 200
    assert payload["level"] == "INFO"
