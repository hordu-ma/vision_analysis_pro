#!/usr/bin/env python3
"""边缘 Agent 使用示例

演示如何使用 EdgeAgent 进行视频/图像推理和结果上报。

Usage:
    # 使用配置文件运行
    python examples/run_edge_agent.py -c config/edge_agent.yaml

    # 使用命令行参数运行
    python examples/run_edge_agent.py --source-type folder --source-path data/images/test

    # 使用环境变量运行
    EDGE_AGENT_SOURCE_TYPE=folder EDGE_AGENT_SOURCE_PATH=data/images/test python examples/run_edge_agent.py
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vision_analysis_pro.edge_agent import (
    CacheConfig,
    EdgeAgent,
    EdgeAgentConfig,
    InferenceConfig,
    ReporterConfig,
    SourceConfig,
    SourceType,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_config_from_args(args: argparse.Namespace) -> EdgeAgentConfig:
    """从命令行参数创建配置"""

    # 数据源配置
    source_config = SourceConfig(
        type=SourceType(args.source_type),
        path=args.source_path,
        fps_limit=args.fps_limit,
        loop=args.loop,
    )

    # 推理配置
    inference_config = InferenceConfig(
        engine=args.engine,
        model_path=args.model_path,
        confidence=args.confidence,
        iou=args.iou,
    )

    # 上报配置
    reporter_config = ReporterConfig(
        type="http",
        url=args.report_url,
        timeout=30.0,
        retry_max=3,
        batch_size=args.batch_size,
        batch_interval=args.batch_interval,
    )

    # 缓存配置
    cache_config = CacheConfig(
        enabled=args.enable_cache,
        db_path=args.cache_path,
    )

    return EdgeAgentConfig(
        device_id=args.device_id,
        log_level=args.log_level,
        source=source_config,
        inference=inference_config,
        reporter=reporter_config,
        cache=cache_config,
        report_only_detections=args.report_only_detections,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="边缘 Agent 使用示例",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 配置文件
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help="YAML 配置文件路径 (如果指定则忽略其他参数)",
    )

    # 设备配置
    parser.add_argument(
        "--device-id",
        type=str,
        default="edge-demo-001",
        help="设备 ID (默认: edge-demo-001)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )

    # 数据源配置
    parser.add_argument(
        "--source-type",
        type=str,
        default="folder",
        choices=["video", "folder", "camera", "rtsp"],
        help="数据源类型 (默认: folder)",
    )
    parser.add_argument(
        "--source-path",
        type=str,
        default="data/images/test",
        help="数据源路径 (默认: data/images/test)",
    )
    parser.add_argument(
        "--fps-limit",
        type=float,
        default=5.0,
        help="帧率限制，0 表示不限制 (默认: 5.0)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="循环播放数据源",
    )

    # 推理配置
    parser.add_argument(
        "--engine",
        type=str,
        default="onnx",
        choices=["onnx", "yolo"],
        help="推理引擎 (默认: onnx)",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="models/best.onnx",
        help="模型文件路径 (默认: models/best.onnx)",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.5,
        help="置信度阈值 (默认: 0.5)",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.5,
        help="IoU 阈值 (默认: 0.5)",
    )

    # 上报配置
    parser.add_argument(
        "--report-url",
        type=str,
        default="http://localhost:8000/api/v1/report",
        help="上报 URL (默认: http://localhost:8000/api/v1/report)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="批量上报大小 (默认: 10)",
    )
    parser.add_argument(
        "--batch-interval",
        type=float,
        default=5.0,
        help="批量上报间隔秒数 (默认: 5.0)",
    )
    parser.add_argument(
        "--report-only-detections",
        action="store_true",
        default=True,
        help="仅上报有检测结果的帧 (默认: True)",
    )

    # 缓存配置
    parser.add_argument(
        "--enable-cache",
        action="store_true",
        default=True,
        help="启用离线缓存 (默认: True)",
    )
    parser.add_argument(
        "--cache-path",
        type=str,
        default="cache/edge_agent.db",
        help="缓存数据库路径 (默认: cache/edge_agent.db)",
    )

    # 其他
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅验证配置，不实际运行",
    )

    args = parser.parse_args()

    try:
        # 加载配置
        if args.config:
            logger.info(f"从配置文件加载: {args.config}")
            config = EdgeAgentConfig.load(args.config)
        else:
            logger.info("从命令行参数创建配置")
            config = create_config_from_args(args)

        # 验证配置
        errors = config.validate()
        if errors:
            logger.error("配置验证失败:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)

        logger.info("配置验证通过")
        logger.info(f"  设备 ID: {config.device_id}")
        logger.info(f"  数据源: {config.source.type.value} - {config.source.path}")
        logger.info(f"  推理引擎: {config.inference.engine}")
        logger.info(f"  模型: {config.inference.model_path}")
        logger.info(f"  上报地址: {config.reporter.url}")

        if args.dry_run:
            logger.info("Dry run 模式，退出")
            sys.exit(0)

        # 创建并运行 Agent
        agent = EdgeAgent(config=config)

        logger.info("=" * 50)
        logger.info("启动边缘 Agent")
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 50)

        agent.run()

    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
