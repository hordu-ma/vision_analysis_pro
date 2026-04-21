"""部署与控制台入口的轻量回归测试。"""

from pathlib import Path

from vision_analysis_pro.settings import Settings
from vision_analysis_pro.web.api import main as api_main


def test_api_server_console_entry_has_help(capsys) -> None:
    """测试 api-server 控制台入口具备可用的参数帮助。"""
    parser = api_main._build_arg_parser()

    try:
        parser.parse_args(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "启动 Vision Analysis Pro API 服务" in captured.out
    assert "--host" in captured.out
    assert "--port" in captured.out


def test_api_server_parser_accepts_runtime_options() -> None:
    """测试 API CLI 可解析运行参数。"""
    parser = api_main._build_arg_parser()
    args = parser.parse_args(["--host", "127.0.0.1", "--port", "9001", "--no-reload"])

    assert args.host == "127.0.0.1"
    assert args.port == 9001
    assert args.reload is False


def test_dockerfile_supports_optional_onnx_install() -> None:
    """测试 Dockerfile 提供 ONNX Runtime 可选安装路径。"""
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "ARG UV_DEFAULT_INDEX=https://pypi.org/simple" in dockerfile
    assert "UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX}" in dockerfile
    assert "ARG INSTALL_ONNX=false" in dockerfile
    assert "uv sync --frozen --extra onnx" in dockerfile
    assert "/app/runs/stage_a_crack/baseline_v0_1/weights/best.pt" in dockerfile
    assert "/app/models/stage_a_crack/best.onnx" in dockerfile


def test_cors_allow_origins_defaults_to_local_frontends() -> None:
    """测试默认 CORS 白名单覆盖本地前端调试与预览端口。"""
    settings = Settings.model_validate({})

    assert settings.cors_allow_origins == "http://localhost:5173,http://localhost:4173"
    assert api_main._parse_cors_allow_origins(settings.cors_allow_origins) == [
        "http://localhost:5173",
        "http://localhost:4173",
    ]


def test_docker_compose_provides_api_and_web_services() -> None:
    """测试统一部署 compose 文件存在前后端服务。"""
    compose_file = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "api:" in compose_file
    assert "web:" in compose_file
    assert "COMPOSE_UV_DEFAULT_INDEX" in compose_file
    assert "CORS_ALLOW_ORIGINS" in compose_file
    assert "./web" in compose_file
    assert "/app/runs/stage_a_crack/baseline_v0_1/weights/best.pt" in compose_file
    assert "/app/models/stage_a_crack/best.onnx" in compose_file


def test_env_example_uses_stage_a_crack_model_paths() -> None:
    """测试本地部署环境示例指向当前 Stage A crack-only 模型路径。"""
    env_file = Path(".env.example").read_text(encoding="utf-8")

    assert "INFERENCE_ENGINE=stub" in env_file
    assert "COMPOSE_UV_DEFAULT_INDEX=https://pypi.org/simple" in env_file
    assert "YOLO_MODEL_PATH=runs/stage_a_crack/baseline_v0_1/weights/best.pt" in env_file
    assert "ONNX_MODEL_PATH=models/stage_a_crack/best.onnx" in env_file
    assert "EDGE_AGENT_INFERENCE_MODEL_PATH=models/stage_a_crack/best.onnx" in env_file


def test_pyproject_pins_default_uv_index_and_prometheus_dependency() -> None:
    """测试项目锁定稳定的 uv 默认索引，并显式声明 Prometheus 指标依赖。"""
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert '"prometheus-client"' in pyproject
    assert 'url = "https://pypi.org/simple"' in pyproject
    assert "default = true" in pyproject


def test_edge_agent_example_uses_stage_a_onnx_model_path() -> None:
    """测试 Edge Agent 示例配置默认指向 Stage A ONNX 模型。"""
    config_file = Path("config/edge_agent.example.yaml").read_text(encoding="utf-8")

    assert 'engine: "onnx"' in config_file
    assert 'model_path: "models/stage_a_crack/best.onnx"' in config_file


def test_frontend_dockerfile_builds_static_bundle() -> None:
    """测试前端 Dockerfile 提供构建与静态托管路径。"""
    dockerfile = Path("web/Dockerfile").read_text(encoding="utf-8")

    assert "npm run build" in dockerfile
    assert "nginx" in dockerfile.lower()


def test_prometheus_alert_rules_example_matches_exported_metrics() -> None:
    """测试告警示例文件使用当前导出的关键指标。"""
    rules = Path("config/prometheus_alert_rules.example.yml").read_text(
        encoding="utf-8"
    )

    assert "VisionApiHigh5xxRate" in rules
    assert "vision_api_request_status_total" in rules
    assert "vision_api_inference_duration_ms_sum" in rules
    assert "vision_api_health_ready_failures_total" in rules


def test_observability_compose_provides_prometheus_and_grafana() -> None:
    """测试监控编排文件提供 Prometheus 与 Grafana 服务。"""
    compose_file = Path("docker-compose.observability.yml").read_text(encoding="utf-8")

    assert "prometheus:" in compose_file
    assert "grafana:" in compose_file
    assert (
        "./config/monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro"
        in compose_file
    )
    assert "prometheus_alert_rules.example.yml" in compose_file


def test_prometheus_scrape_config_targets_api_metrics() -> None:
    """测试 Prometheus 抓取配置指向 API metrics 端点。"""
    config_text = Path("config/monitoring/prometheus/prometheus.yml").read_text(
        encoding="utf-8"
    )

    assert "metrics_path: /api/v1/metrics" in config_text
    assert "api:8000" in config_text
    assert "/etc/prometheus/rules/*.yml" in config_text


def test_grafana_provisioning_includes_prometheus_and_dashboard() -> None:
    """测试 Grafana 预置了 Prometheus 数据源与基础仪表盘。"""
    datasource_text = Path(
        "config/monitoring/grafana/provisioning/datasources/datasources.yml"
    ).read_text(encoding="utf-8")
    dashboard_provider_text = Path(
        "config/monitoring/grafana/provisioning/dashboards/dashboards.yml"
    ).read_text(encoding="utf-8")
    dashboard_text = Path(
        "config/monitoring/grafana/dashboards/vision-api-overview.json"
    ).read_text(encoding="utf-8")

    assert "type: prometheus" in datasource_text
    assert "url: http://prometheus:9090" in datasource_text
    assert "/var/lib/grafana/dashboards" in dashboard_provider_text
    assert '"uid": "vision-api-overview"' in dashboard_text
    assert '"title": "Vision API Overview"' in dashboard_text
