"""YOLO 模型 ONNX 导出脚本

将 PyTorch 模型 (.pt) 导出为 ONNX 格式 (.onnx)，用于跨平台部署和推理加速。

使用方法:
    python scripts/export_onnx.py
    python scripts/export_onnx.py --model runs/train/exp/weights/best.pt --output models/best.onnx
    python scripts/export_onnx.py --model yolov8n.pt --simplify --half

导出后可使用 ONNX Runtime 进行推理。
"""

import argparse
from pathlib import Path

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="将 YOLO PyTorch 模型导出为 ONNX 格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 导出默认训练模型
  python scripts/export_onnx.py

  # 导出指定模型到指定位置
  python scripts/export_onnx.py --model runs/train/exp/weights/best.pt --output models/best.onnx

  # 导出并简化 ONNX 模型
  python scripts/export_onnx.py --simplify

  # 导出 FP16 半精度模型（需要 GPU）
  python scripts/export_onnx.py --half
        """,
    )

    # 输入输出配置
    parser.add_argument(
        "--model",
        type=str,
        default="runs/train/exp/weights/best.pt",
        help="输入 PyTorch 模型路径 (.pt)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出 ONNX 模型路径（默认与输入同目录同名）",
    )

    # 导出参数
    parser.add_argument(
        "--imgsz",
        type=int,
        nargs="+",
        default=[640],
        help="输入图像尺寸，单值或 [height, width]",
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=1,
        help="批次大小（静态导出）",
    )

    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="启用动态输入尺寸（batch, height, width）",
    )

    parser.add_argument(
        "--half",
        action="store_true",
        help="导出 FP16 半精度模型（需要 GPU 支持）",
    )

    parser.add_argument(
        "--simplify",
        action="store_true",
        help="使用 onnxslim 简化模型（需安装 onnxslim）",
    )

    parser.add_argument(
        "--opset",
        type=int,
        default=17,
        help="ONNX opset 版本（默认 17）",
    )

    # 设备配置
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="导出设备 (cpu, 0, cuda:0 等)",
    )

    # 验证配置
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="跳过导出后的验证步骤",
    )

    return parser.parse_args()


def export_onnx(
    model_path: str,
    output_path: str | None = None,
    imgsz: list[int] | None = None,
    batch: int = 1,
    dynamic: bool = False,
    half: bool = False,
    simplify: bool = False,
    opset: int = 17,
    device: str = "cpu",
) -> Path:
    """导出 ONNX 模型

    Args:
        model_path: 输入 PyTorch 模型路径
        output_path: 输出 ONNX 路径（None 则自动生成）
        imgsz: 输入图像尺寸
        batch: 批次大小
        dynamic: 是否启用动态尺寸
        half: 是否使用 FP16
        simplify: 是否简化模型
        opset: ONNX opset 版本
        device: 导出设备

    Returns:
        导出的 ONNX 文件路径
    """
    if imgsz is None:
        imgsz = [640]

    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"模型文件不存在: {model_path}")

    print(f"📦 加载模型: {model_path}")
    model = YOLO(str(model_path))

    print("🔄 开始导出 ONNX...")

    # 调用 Ultralytics 的 export 方法
    export_path = model.export(
        format="onnx",
        imgsz=imgsz,
        batch=batch,
        dynamic=dynamic,
        half=half,
        simplify=simplify,
        opset=opset,
        device=device,
    )

    export_path = Path(export_path)

    # 如果指定了输出路径，移动文件
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if export_path != output_path:
            import shutil

            shutil.move(str(export_path), str(output_path))
            export_path = output_path
            print(f"📁 移动到: {output_path}")

    return export_path


def verify_onnx(onnx_path: Path) -> bool:
    """验证导出的 ONNX 模型

    Args:
        onnx_path: ONNX 模型路径

    Returns:
        验证是否通过
    """
    print("\n🔍 验证 ONNX 模型...")

    try:
        import onnx

        # 加载并检查模型
        model = onnx.load(str(onnx_path))
        onnx.checker.check_model(model)

        # 打印模型信息
        print("  ✅ ONNX 模型格式正确")

        # 获取输入输出信息
        graph = model.graph

        print("\n  📥 输入:")
        for inp in graph.input:
            shape = [
                d.dim_value if d.dim_value > 0 else d.dim_param
                for d in inp.type.tensor_type.shape.dim
            ]
            print(f"     - {inp.name}: {shape}")

        print("\n  📤 输出:")
        for out in graph.output:
            shape = [
                d.dim_value if d.dim_value > 0 else d.dim_param
                for d in out.type.tensor_type.shape.dim
            ]
            print(f"     - {out.name}: {shape}")

        # 打印文件大小
        file_size = onnx_path.stat().st_size / (1024 * 1024)
        print(f"\n  📊 文件大小: {file_size:.2f} MB")

        return True

    except ImportError:
        print("  ⚠️  未安装 onnx 库，跳过详细验证")
        print("     安装: uv add onnx")
        return True

    except Exception as e:
        print(f"  ❌ 验证失败: {e}")
        return False


def main() -> None:
    """主函数"""
    args = parse_args()

    print("=" * 60)
    print("🚀 YOLO 模型 ONNX 导出工具")
    print("=" * 60)

    # 打印配置
    print("\n📋 导出配置:")
    print(f"  输入模型:   {args.model}")
    print(f"  输出路径:   {args.output or '(自动生成)'}")
    print(f"  图像尺寸:   {args.imgsz}")
    print(f"  批次大小:   {args.batch}")
    print(f"  动态尺寸:   {args.dynamic}")
    print(f"  半精度:     {args.half}")
    print(f"  简化模型:   {args.simplify}")
    print(f"  Opset:      {args.opset}")
    print(f"  导出设备:   {args.device}")

    print("\n" + "-" * 60)

    try:
        # 执行导出
        onnx_path = export_onnx(
            model_path=args.model,
            output_path=args.output,
            imgsz=args.imgsz,
            batch=args.batch,
            dynamic=args.dynamic,
            half=args.half,
            simplify=args.simplify,
            opset=args.opset,
            device=args.device,
        )

        print(f"\n✅ 导出成功: {onnx_path}")

        # 验证模型
        if not args.no_verify:
            verify_onnx(onnx_path)

        print("\n" + "=" * 60)
        print("🎉 ONNX 导出完成！")
        print("=" * 60)

        # 使用提示
        print("\n📝 后续步骤:")
        print("  1. 使用 ONNX Runtime 推理:")
        print("     import onnxruntime as ort")
        print(f"     session = ort.InferenceSession('{onnx_path}')")
        print("\n  2. 或复制到 models/ 目录:")
        print(f"     cp {onnx_path} models/best.onnx")

    except FileNotFoundError as e:
        print(f"\n❌ 错误: {e}")
        print("   请确认模型路径正确，或先运行训练脚本")
        raise SystemExit(1) from e

    except Exception as e:
        print(f"\n❌ 导出失败: {e}")
        raise


if __name__ == "__main__":
    main()
