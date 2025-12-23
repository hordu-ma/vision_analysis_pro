"""边缘推理 Agent 主程序

实现完整的视频/图像采集 → 推理 → 结果上报流程。
支持多种数据源、推理引擎和上报方式。
"""

import logging
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Any

from ..core.inference import InferenceEngine, ONNXInferenceEngine, YOLOInferenceEngine
from .config import EdgeAgentConfig
from .models import Detection, FrameData, InferenceResult, ReportPayload, ReportStatus
from .reporters import create_reporter
from .sources import create_source

logger = logging.getLogger(__name__)


class EdgeAgent:
    """边缘设备推理 Agent

    负责从数据源采集图像/视频帧，执行推理，并将结果上报到云端。

    主要功能：
    - 支持多种数据源（视频文件、图像文件夹、摄像头、RTSP 流）
    - 支持多种推理引擎（ONNX、YOLO）
    - 支持 HTTP 上报（含重试和离线缓存）
    - 支持优雅关闭

    Attributes:
        config: Agent 配置
    """

    def __init__(
        self,
        config: EdgeAgentConfig | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        """初始化 Agent

        Args:
            config: Agent 配置对象，如果为 None 则从 config_path 加载
            config_path: 配置文件路径

        Raises:
            ValueError: 配置无效
            FileNotFoundError: 配置文件不存在
        """
        # 加载配置
        if config is not None:
            self.config = config
        elif config_path is not None:
            self.config = EdgeAgentConfig.load(config_path)
        else:
            # 使用默认配置 + 环境变量
            self.config = EdgeAgentConfig.load()

        # 配置日志
        self._setup_logging()

        logger.info(f"初始化 Edge Agent: {self.config.device_id}")

        # 内部状态
        self._running = False
        self._stop_event = threading.Event()
        self._inference_engine: InferenceEngine | None = None
        self._report_queue: Queue[ReportPayload] = Queue()
        self._reporter_thread: threading.Thread | None = None

        # 统计信息
        self._stats = {
            "frames_processed": 0,
            "detections_total": 0,
            "reports_sent": 0,
            "reports_failed": 0,
            "reports_cached": 0,
            "start_time": None,
            "last_frame_time": None,
        }

        # 注册信号处理
        self._setup_signal_handlers()

    def _setup_logging(self) -> None:
        """配置日志"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)

        # 配置根日志
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 设置 edge_agent 模块日志级别
        logging.getLogger("vision_analysis_pro.edge_agent").setLevel(log_level)

    def _setup_signal_handlers(self) -> None:
        """设置信号处理器以支持优雅关闭"""

        def signal_handler(signum: int, frame: Any) -> None:
            sig_name = signal.Signals(signum).name
            logger.info(f"收到信号 {sig_name}，正在停止 Agent...")
            self.stop()

        # 注册 SIGINT (Ctrl+C) 和 SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _create_inference_engine(self) -> InferenceEngine:
        """创建推理引擎

        Returns:
            推理引擎实例

        Raises:
            ValueError: 不支持的引擎类型
            FileNotFoundError: 模型文件不存在
        """
        engine_type = self.config.inference.engine.lower()
        model_path = Path(self.config.inference.model_path)

        logger.info(f"创建推理引擎: {engine_type}, 模型: {model_path}")

        if engine_type == "onnx":
            engine = ONNXInferenceEngine(model_path)
        elif engine_type == "yolo":
            engine = YOLOInferenceEngine(model_path)
        else:
            raise ValueError(
                f"不支持的推理引擎类型: {engine_type}，支持的类型: ['onnx', 'yolo']"
            )

        # 预热模型
        if self.config.inference.warmup:
            logger.info("预热推理引擎...")
            engine.warmup()

        return engine

    def _run_inference(self, frame: FrameData) -> InferenceResult:
        """执行推理

        Args:
            frame: 帧数据

        Returns:
            推理结果
        """
        if self._inference_engine is None:
            raise RuntimeError("推理引擎未初始化")

        start_time = time.perf_counter()

        # 执行推理
        raw_results = self._inference_engine.predict(
            frame.image,
            conf=self.config.inference.confidence,
            iou=self.config.inference.iou,
        )

        inference_time_ms = (time.perf_counter() - start_time) * 1000

        # 转换结果格式
        detections = [
            Detection(
                label=r["label"],
                confidence=r["confidence"],
                bbox=r["bbox"],
            )
            for r in raw_results
        ]

        return InferenceResult(
            frame_id=frame.frame_id,
            timestamp=frame.timestamp,
            source_id=frame.source_id,
            detections=detections,
            inference_time_ms=inference_time_ms,
            metadata=frame.metadata,
        )

    def _reporter_worker(self) -> None:
        """上报工作线程

        从队列中取出数据并上报到云端。
        """
        logger.info("上报工作线程启动")

        reporter = create_reporter(
            self.config.reporter,
            self.config.cache if self.config.cache.enabled else None,
        )

        with reporter:
            last_flush_time = time.time()

            while not self._stop_event.is_set():
                try:
                    # 尝试从队列获取数据
                    payload = self._report_queue.get(timeout=1.0)

                    # 上报
                    status = reporter.report_sync(payload)

                    if status == ReportStatus.SUCCESS:
                        self._stats["reports_sent"] += 1
                        logger.debug(
                            f"上报成功: {payload.batch_id} "
                            f"({payload.total_detections} 检测)"
                        )
                    elif status == ReportStatus.CACHED:
                        self._stats["reports_cached"] += 1
                        logger.debug(f"上报已缓存: {payload.batch_id}")
                    else:
                        self._stats["reports_failed"] += 1
                        logger.warning(f"上报失败: {payload.batch_id}")

                    self._report_queue.task_done()

                except Empty:
                    pass

                # 定期刷新缓存
                current_time = time.time()
                if current_time - last_flush_time >= self.config.cache.flush_interval:
                    if hasattr(reporter, "flush_cache_sync"):
                        flushed = reporter.flush_cache_sync()
                        if flushed > 0:
                            self._stats["reports_sent"] += flushed
                            logger.info(f"缓存刷新: {flushed} 条成功")

                    # 清理过期缓存
                    if hasattr(reporter, "cleanup_cache"):
                        reporter.cleanup_cache()

                    last_flush_time = current_time

        logger.info("上报工作线程停止")

    def _process_frame(self, frame: FrameData) -> InferenceResult | None:
        """处理单帧

        Args:
            frame: 帧数据

        Returns:
            推理结果，如果配置为仅上报有检测的帧且无检测则返回 None
        """
        # 执行推理
        result = self._run_inference(frame)

        # 更新统计
        self._stats["frames_processed"] += 1
        self._stats["detections_total"] += result.detection_count
        self._stats["last_frame_time"] = datetime.now().isoformat()

        # 日志
        if result.has_detections:
            logger.info(
                f"帧 {frame.frame_id}: 检测到 {result.detection_count} 个目标 "
                f"(推理耗时: {result.inference_time_ms:.1f}ms)"
            )
        else:
            logger.debug(
                f"帧 {frame.frame_id}: 无检测 "
                f"(推理耗时: {result.inference_time_ms:.1f}ms)"
            )

        # 根据配置决定是否返回结果
        if self.config.report_only_detections and not result.has_detections:
            return None

        return result

    def run(self) -> None:
        """启动 Agent 主循环

        执行采集 → 推理 → 上报的完整流程。

        Raises:
            RuntimeError: Agent 已在运行
        """
        if self._running:
            raise RuntimeError("Agent 已在运行")

        # 验证配置
        errors = self.config.validate()
        if errors:
            for error in errors:
                logger.error(f"配置错误: {error}")
            raise ValueError(f"配置验证失败: {errors}")

        logger.info("Edge Agent 启动中...")
        self._running = True
        self._stop_event.clear()
        self._stats["start_time"] = datetime.now().isoformat()

        try:
            # 创建推理引擎
            self._inference_engine = self._create_inference_engine()

            # 启动上报线程
            self._reporter_thread = threading.Thread(
                target=self._reporter_worker,
                name="reporter-worker",
                daemon=True,
            )
            self._reporter_thread.start()

            # 创建数据源
            source = create_source(self.config.source, self.config.device_id)

            # 结果缓冲区（用于批量上报）
            results_buffer: list[InferenceResult] = []
            last_report_time = time.time()

            with source:
                logger.info(f"数据源已打开: {source.get_info()}")

                for frame in source:
                    if self._stop_event.is_set():
                        logger.info("收到停止信号，退出主循环")
                        break

                    # 处理帧
                    result = self._process_frame(frame)
                    if result is not None:
                        results_buffer.append(result)

                    # 检查是否需要上报
                    should_report = len(
                        results_buffer
                    ) >= self.config.reporter.batch_size or (
                        results_buffer
                        and time.time() - last_report_time
                        >= self.config.reporter.batch_interval
                    )

                    if should_report:
                        payload = ReportPayload(
                            device_id=self.config.device_id,
                            results=results_buffer.copy(),
                        )
                        self._report_queue.put(payload)
                        results_buffer.clear()
                        last_report_time = time.time()

                # 处理剩余的结果
                if results_buffer:
                    payload = ReportPayload(
                        device_id=self.config.device_id,
                        results=results_buffer,
                    )
                    self._report_queue.put(payload)

            logger.info("数据源处理完成")

        except KeyboardInterrupt:
            logger.info("收到键盘中断")

        except Exception as e:
            logger.exception(f"Agent 运行出错: {e}")
            raise

        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """清理资源"""
        logger.info("正在清理资源...")

        # 等待上报队列处理完成
        if not self._report_queue.empty():
            logger.info(f"等待上报队列处理完成 ({self._report_queue.qsize()} 条待处理)")
            try:
                self._report_queue.join()
            except Exception:
                pass

        # 停止上报线程
        self._stop_event.set()
        if self._reporter_thread and self._reporter_thread.is_alive():
            self._reporter_thread.join(timeout=5.0)

        self._running = False
        self._inference_engine = None

        logger.info("Edge Agent 已停止")
        self._print_stats()

    def stop(self) -> None:
        """停止 Agent

        设置停止标志，主循环会在下一次迭代时退出。
        """
        if not self._running:
            return

        logger.info("Edge Agent 停止中...")
        self._stop_event.set()

    @property
    def is_running(self) -> bool:
        """Agent 是否正在运行"""
        return self._running

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            包含运行统计的字典
        """
        stats = self._stats.copy()
        stats["is_running"] = self._running
        stats["queue_size"] = self._report_queue.qsize()

        if stats["start_time"]:
            start = datetime.fromisoformat(stats["start_time"])
            elapsed = (datetime.now() - start).total_seconds()
            stats["elapsed_seconds"] = round(elapsed, 2)

            if elapsed > 0:
                stats["fps"] = round(stats["frames_processed"] / elapsed, 2)

        return stats

    def _print_stats(self) -> None:
        """打印统计信息"""
        stats = self.get_stats()

        logger.info("=" * 50)
        logger.info("Edge Agent 运行统计")
        logger.info("=" * 50)
        logger.info(f"处理帧数: {stats['frames_processed']}")
        logger.info(f"检测总数: {stats['detections_total']}")
        logger.info(f"成功上报: {stats['reports_sent']}")
        logger.info(f"上报失败: {stats['reports_failed']}")
        logger.info(f"已缓存: {stats['reports_cached']}")

        if "elapsed_seconds" in stats:
            logger.info(f"运行时长: {stats['elapsed_seconds']:.1f} 秒")

        if "fps" in stats:
            logger.info(f"平均帧率: {stats['fps']:.2f} fps")

        logger.info("=" * 50)


def main() -> None:
    """CLI 入口点"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Vision Analysis Pro - 边缘推理 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help="配置文件路径 (YAML 格式)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="启用详细日志输出",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="Edge Agent 0.1.0",
    )

    args = parser.parse_args()

    # 如果启用详细日志，设置环境变量
    if args.verbose:
        import os

        os.environ["EDGE_AGENT_LOG_LEVEL"] = "DEBUG"

    try:
        agent = EdgeAgent(config_path=args.config)
        agent.run()
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
