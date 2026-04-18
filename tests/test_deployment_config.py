"""部署与控制台入口的轻量回归测试。"""

from pathlib import Path

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
    args = parser.parse_args(
        ["--host", "127.0.0.1", "--port", "9001", "--no-reload"]
    )

    assert args.host == "127.0.0.1"
    assert args.port == 9001
    assert args.reload is False


def test_dockerfile_supports_optional_onnx_install() -> None:
    """测试 Dockerfile 提供 ONNX Runtime 可选安装路径。"""
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "ARG INSTALL_ONNX=false" in dockerfile
    assert "uv sync --frozen --extra onnx" in dockerfile
