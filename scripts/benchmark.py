"""推理引擎性能基准测试脚本

对比 YOLO 和 ONNX Runtime 引擎的推理性能，输出详细的性能报告。

使用方法:
    python scripts/benchmark.py
    python scripts/benchmark.py --iterations 50 --warmup 5
    python scripts/benchmark.py --engine onnx --image test_image.jpg
    python scripts/benchmark.py --batch-sizes 1 4 8 16

输出指标:
    - 平均推理时间 (ms)
    - 最小/最大推理时间 (ms)
    - 标准差 (ms)
    - 吞吐量 (FPS)
    - P50/P95/P99 延迟
"""

import argparse
import gc
import statistics
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="推理引擎性能基准测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行默认基准测试（YOLO + ONNX 对比）
  python scripts/benchmark.py

  # 仅测试 ONNX 引擎
  python scripts/benchmark.py --engine onnx

  # 使用自定义图像和迭代次数
  python scripts/benchmark.py --image path/to/image.jpg --iterations 100

  # 测试不同批次大小（仅 ONNX 支持）
  python scripts/benchmark.py --engine onnx --batch-sizes 1 4 8
        """,
    )

    parser.add_argument(
        "--engine",
        type=str,
        choices=["yolo", "onnx", "both"],
        default="both",
        help="要测试的引擎类型（默认: both）",
    )

    parser.add_argument(
        "--yolo-model",
        type=str,
        default="runs/train/exp/weights/best.pt",
        help="YOLO 模型路径",
    )

    parser.add_argument(
        "--onnx-model",
        type=str,
        default="models/best.onnx",
        help="ONNX 模型路径",
    )

    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="测试图像路径（默认使用合成图像）",
    )

    parser.add_argument(
        "--imgsz",
        type=int,
        nargs="+",
        default=[640],
        help="输入图像尺寸（默认: 640）",
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=30,
        help="推理迭代次数（默认: 30）",
    )

    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="预热迭代次数（默认: 5）",
    )

    parser.add_argument(
        "--conf",
        type=float,
        default=0.5,
        help="置信度阈值（默认: 0.5）",
    )

    parser.add_argument(
        "--iou",
        type=float,
        default=0.5,
        help="NMS IoU 阈值（默认: 0.5）",
    )

    parser.add_argument(
        "--batch-sizes",
        type=int,
        nargs="+",
        default=[1],
        help="批次大小列表（默认: 1）",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出报告文件路径（可选）",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细输出",
    )

    return parser.parse_args()


def create_synthetic_image(height: int = 480, width: int = 640) -> np.ndarray:
    """创建合成测试图像

    Args:
        height: 图像高度
        width: 图像宽度

    Returns:
        BGR 格式的 numpy 数组
    """
    # 创建随机背景
    img = np.random.randint(100, 150, (height, width, 3), dtype=np.uint8)

    # 添加一些形状模拟目标
    cv2.rectangle(img, (100, 100), (200, 200), (0, 0, 255), 2)
    cv2.circle(img, (400, 300), 50, (0, 255, 0), -1)
    cv2.line(img, (50, 400), (300, 450), (255, 0, 0), 3)

    return img


def percentile(data: list[float], p: float) -> float:
    """计算百分位数

    Args:
        data: 数据列表
        p: 百分位（0-100）

    Returns:
        百分位值
    """
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def benchmark_engine(
    engine: Any,
    image: np.ndarray,
    iterations: int,
    warmup: int,
    conf: float,
    iou: float,
    verbose: bool = False,
) -> dict[str, Any]:
    """对单个引擎进行基准测试

    Args:
        engine: 推理引擎实例
        image: 测试图像
        iterations: 测试迭代次数
        warmup: 预热迭代次数
        conf: 置信度阈值
        iou: IoU 阈值
        verbose: 是否显示详细输出

    Returns:
        性能指标字典
    """
    latencies: list[float] = []

    # 预热
    if verbose:
        print(f"  预热中 ({warmup} 次)...", end=" ", flush=True)

    for _ in range(warmup):
        _ = engine.predict(image, conf=conf, iou=iou)

    if verbose:
        print("完成")

    # 强制垃圾回收
    gc.collect()

    # 正式测试
    if verbose:
        print(f"  测试中 ({iterations} 次)...", end=" ", flush=True)

    for i in range(iterations):
        start = time.perf_counter()
        detections = engine.predict(image, conf=conf, iou=iou)
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

        if verbose and (i + 1) % 10 == 0:
            print(f"{i + 1}", end=" ", flush=True)

    if verbose:
        print("完成")

    # 计算统计指标
    avg_latency = statistics.mean(latencies)
    std_latency = statistics.stdev(latencies) if len(latencies) > 1 else 0
    min_latency = min(latencies)
    max_latency = max(latencies)
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    fps = 1000 / avg_latency if avg_latency > 0 else 0

    return {
        "iterations": iterations,
        "avg_latency_ms": avg_latency,
        "std_latency_ms": std_latency,
        "min_latency_ms": min_latency,
        "max_latency_ms": max_latency,
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "p99_latency_ms": p99,
        "fps": fps,
        "num_detections": len(detections),
        "latencies": latencies,
    }


def print_results(name: str, results: dict[str, Any]) -> None:
    """打印测试结果

    Args:
        name: 引擎名称
        results: 测试结果字典
    """
    print(f"\n  📊 {name} 性能指标:")
    print(f"     迭代次数:     {results['iterations']}")
    print(f"     平均延迟:     {results['avg_latency_ms']:.2f} ms")
    print(f"     标准差:       {results['std_latency_ms']:.2f} ms")
    print(f"     最小延迟:     {results['min_latency_ms']:.2f} ms")
    print(f"     最大延迟:     {results['max_latency_ms']:.2f} ms")
    print(f"     P50 延迟:     {results['p50_latency_ms']:.2f} ms")
    print(f"     P95 延迟:     {results['p95_latency_ms']:.2f} ms")
    print(f"     P99 延迟:     {results['p99_latency_ms']:.2f} ms")
    print(f"     吞吐量:       {results['fps']:.2f} FPS")
    print(f"     检测数量:     {results['num_detections']}")


def print_comparison(
    yolo_results: dict[str, Any], onnx_results: dict[str, Any]
) -> None:
    """打印对比结果

    Args:
        yolo_results: YOLO 测试结果
        onnx_results: ONNX 测试结果
    """
    print("\n" + "=" * 60)
    print("📈 性能对比")
    print("=" * 60)

    speedup = yolo_results["avg_latency_ms"] / onnx_results["avg_latency_ms"]
    fps_diff = onnx_results["fps"] - yolo_results["fps"]

    print(f"\n  {'指标':<20} {'YOLO':>12} {'ONNX':>12} {'差异':>12}")
    print(f"  {'-' * 56}")
    print(
        f"  {'平均延迟 (ms)':<20} {yolo_results['avg_latency_ms']:>12.2f} "
        f"{onnx_results['avg_latency_ms']:>12.2f} "
        f"{speedup:>11.2f}x"
    )
    print(
        f"  {'P95 延迟 (ms)':<20} {yolo_results['p95_latency_ms']:>12.2f} "
        f"{onnx_results['p95_latency_ms']:>12.2f} "
        f"{yolo_results['p95_latency_ms'] / onnx_results['p95_latency_ms']:>11.2f}x"
    )
    print(
        f"  {'吞吐量 (FPS)':<20} {yolo_results['fps']:>12.2f} "
        f"{onnx_results['fps']:>12.2f} "
        f"{'+' if fps_diff > 0 else ''}{fps_diff:>10.2f}"
    )

    print(f"\n  🏆 ONNX 相对 YOLO 加速比: {speedup:.2f}x")

    if speedup > 1:
        print(f"     ONNX 更快 {(speedup - 1) * 100:.1f}%")
    elif speedup < 1:
        print(f"     YOLO 更快 {(1 - speedup) * 100:.1f}%")
    else:
        print("     性能相当")


def save_report(
    results: dict[str, dict[str, Any]],
    output_path: str,
    args: argparse.Namespace,
) -> None:
    """保存性能报告

    Args:
        results: 所有测试结果
        output_path: 输出文件路径
        args: 命令行参数
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 推理引擎性能基准测试报告\n\n")
        f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 测试配置\n\n")
        f.write(f"- 图像尺寸: {args.imgsz}\n")
        f.write(f"- 迭代次数: {args.iterations}\n")
        f.write(f"- 预热次数: {args.warmup}\n")
        f.write(f"- 置信度阈值: {args.conf}\n")
        f.write(f"- IoU 阈值: {args.iou}\n\n")

        f.write("## 测试结果\n\n")
        f.write("| 引擎 | 平均延迟 (ms) | P95 (ms) | P99 (ms) | FPS |\n")
        f.write("|------|--------------|----------|----------|-----|\n")

        for name, res in results.items():
            f.write(
                f"| {name} | {res['avg_latency_ms']:.2f} | "
                f"{res['p95_latency_ms']:.2f} | {res['p99_latency_ms']:.2f} | "
                f"{res['fps']:.2f} |\n"
            )

        if "YOLO" in results and "ONNX" in results:
            speedup = (
                results["YOLO"]["avg_latency_ms"] / results["ONNX"]["avg_latency_ms"]
            )
            f.write("\n## 对比结论\n\n")
            f.write(f"ONNX 相对 YOLO 加速比: **{speedup:.2f}x**\n")

    print(f"\n📄 报告已保存到: {output_path}")


def main() -> None:
    """主函数"""
    args = parse_args()

    print("=" * 60)
    print("🚀 推理引擎性能基准测试")
    print("=" * 60)

    # 打印配置
    print("\n📋 测试配置:")
    print(f"  测试引擎:   {args.engine}")
    print(f"  图像尺寸:   {args.imgsz}")
    print(f"  迭代次数:   {args.iterations}")
    print(f"  预热次数:   {args.warmup}")
    print(f"  置信度:     {args.conf}")
    print(f"  IoU 阈值:   {args.iou}")

    # 加载或创建测试图像
    if args.image:
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"\n❌ 图像文件不存在: {args.image}")
            return
        image = cv2.imread(str(image_path))
        print(f"  测试图像:   {args.image} ({image.shape[1]}x{image.shape[0]})")
    else:
        h = args.imgsz[0] if len(args.imgsz) == 1 else args.imgsz[0]
        w = args.imgsz[1] if len(args.imgsz) > 1 else args.imgsz[0]
        image = create_synthetic_image(h, w)
        print(f"  测试图像:   合成图像 ({w}x{h})")

    results: dict[str, dict[str, Any]] = {}

    # 测试 YOLO 引擎
    if args.engine in ["yolo", "both"]:
        print("\n" + "-" * 60)
        print("🔷 测试 YOLO 引擎")
        print("-" * 60)

        yolo_path = Path(args.yolo_model)
        if not yolo_path.exists():
            print(f"  ⚠️  YOLO 模型不存在: {args.yolo_model}")
            print("     跳过 YOLO 测试")
        else:
            try:
                from vision_analysis_pro.core.inference import YOLOInferenceEngine

                print(f"  模型路径:   {args.yolo_model}")
                print("  加载模型...", end=" ", flush=True)
                yolo_engine = YOLOInferenceEngine(yolo_path)
                print("完成")

                yolo_results = benchmark_engine(
                    yolo_engine,
                    image,
                    args.iterations,
                    args.warmup,
                    args.conf,
                    args.iou,
                    args.verbose,
                )
                results["YOLO"] = yolo_results
                print_results("YOLO", yolo_results)

            except ImportError as e:
                print(f"  ❌ 无法加载 YOLO 引擎: {e}")
            except Exception as e:
                print(f"  ❌ YOLO 测试失败: {e}")

    # 测试 ONNX 引擎
    if args.engine in ["onnx", "both"]:
        print("\n" + "-" * 60)
        print("🔶 测试 ONNX 引擎")
        print("-" * 60)

        onnx_path = Path(args.onnx_model)
        if not onnx_path.exists():
            print(f"  ⚠️  ONNX 模型不存在: {args.onnx_model}")
            print("     跳过 ONNX 测试")
        else:
            try:
                from vision_analysis_pro.core.inference import ONNXInferenceEngine

                print(f"  模型路径:   {args.onnx_model}")
                print("  加载模型...", end=" ", flush=True)
                onnx_engine = ONNXInferenceEngine(onnx_path)
                print("完成")
                print(f"  执行提供者: {', '.join(onnx_engine.providers)}")

                onnx_results = benchmark_engine(
                    onnx_engine,
                    image,
                    args.iterations,
                    args.warmup,
                    args.conf,
                    args.iou,
                    args.verbose,
                )
                results["ONNX"] = onnx_results
                print_results("ONNX", onnx_results)

            except ImportError as e:
                print(f"  ❌ 无法加载 ONNX 引擎: {e}")
                print("     请运行: uv sync --extra onnx")
            except Exception as e:
                print(f"  ❌ ONNX 测试失败: {e}")

    # 打印对比结果
    if "YOLO" in results and "ONNX" in results:
        print_comparison(results["YOLO"], results["ONNX"])

    # 保存报告
    if args.output:
        save_report(results, args.output, args)

    print("\n" + "=" * 60)
    print("✅ 基准测试完成！")
    print("=" * 60)

    # 使用提示
    if not results:
        print("\n⚠️  未能完成任何测试，请检查模型文件是否存在")
    else:
        print("\n📝 提示:")
        print("  - 使用 --iterations 增加迭代次数以获得更稳定的结果")
        print("  - 使用 --output report.md 保存测试报告")
        print("  - 使用 --verbose 查看详细进度")


if __name__ == "__main__":
    main()
