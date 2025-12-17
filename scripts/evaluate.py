"""模型评估脚本

使用训练好的 YOLO 模型评估验证集或测试集性能。

使用方法:
    python scripts/evaluate.py --model runs/train/exp/weights/best.pt
    python scripts/evaluate.py --model runs/train/exp/weights/best.pt --split test
"""

import argparse
from pathlib import Path

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="评估 YOLO 模型")

    # 模型配置
    parser.add_argument(
        "--model",
        type=str,
        default="runs/train/exp/weights/best.pt",
        help="训练好的模型路径",
    )

    # 数据配置
    parser.add_argument(
        "--data",
        type=str,
        default="data/data.yaml",
        help="数据集配置文件路径",
    )

    parser.add_argument(
        "--split",
        type=str,
        default="val",
        choices=["train", "val", "test"],
        help="评估数据集切分 (train/val/test)",
    )

    # 评估参数
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="输入图像尺寸",
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=8,
        help="批次大小",
    )

    parser.add_argument(
        "--conf",
        type=float,
        default=0.001,
        help="置信度阈值",
    )

    parser.add_argument(
        "--iou",
        type=float,
        default=0.6,
        help="NMS IoU 阈值",
    )

    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="评估设备 (cpu, 0, 0,1 等)",
    )

    # 输出配置
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="是否保存 JSON 格式结果",
    )

    parser.add_argument(
        "--save-hybrid",
        action="store_true",
        help="是否保存混合标签（ground truth + predictions）",
    )

    parser.add_argument(
        "--plots",
        action="store_true",
        default=True,
        help="是否生成评估图表",
    )

    return parser.parse_args()


def main() -> None:
    """主评估函数"""
    args = parse_args()

    print("=" * 60)
    print("📊 YOLO 模型评估")
    print("=" * 60)

    # 检查模型文件
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"\n❌ 错误: 模型文件不存在: {model_path}")
        print("   请先运行 scripts/train.py 训练模型")
        return

    # 检查数据配置文件
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"\n❌ 错误: 数据配置文件不存在: {data_path}")
        return

    print("\n📋 评估配置:")
    print(f"  模型路径:   {args.model}")
    print(f"  数据配置:   {args.data}")
    print(f"  评估切分:   {args.split}")
    print(f"  图像尺寸:   {args.imgsz}")
    print(f"  批次大小:   {args.batch}")
    print(f"  置信度阈值: {args.conf}")
    print(f"  IoU 阈值:   {args.iou}")
    print(f"  评估设备:   {args.device}")

    print("\n" + "=" * 60)
    print("🔍 开始评估...")
    print("=" * 60 + "\n")

    # 加载模型
    model = YOLO(args.model)

    # 评估模型
    try:
        results = model.val(
            data=args.data,
            split=args.split,
            imgsz=args.imgsz,
            batch=args.batch,
            conf=args.conf,
            iou=args.iou,
            device=args.device,
            save_json=args.save_json,
            save_hybrid=args.save_hybrid,
            plots=args.plots,
            verbose=True,
        )

        print("\n" + "=" * 60)
        print("✅ 评估完成！")
        print("=" * 60)

        # 打印评估结果
        print("\n📈 整体性能指标:")
        print(f"  mAP50:          {results.box.map50:.4f}")
        print(f"  mAP50-95:       {results.box.map:.4f}")
        print(
            f"  Precision:      {results.box.p.mean() if hasattr(results.box, 'p') else 0:.4f}"
        )
        print(
            f"  Recall:         {results.box.r.mean() if hasattr(results.box, 'r') else 0:.4f}"
        )
        print(
            f"  F1-Score:       {results.box.f1.mean() if hasattr(results.box, 'f1') else 0:.4f}"
        )

        # 打印各类别性能
        if hasattr(results.box, "maps") and len(results.box.maps) > 0:
            print("\n📊 各类别 mAP50-95:")
            class_names = model.names
            for i, map_val in enumerate(results.box.maps):
                class_name = class_names.get(i, f"class_{i}")
                print(f"  {class_name:12s}: {map_val:.4f}")

        # 打印速度统计
        if hasattr(results, "speed"):
            print("\n⚡ 推理速度:")
            speed = results.speed
            print(f"  预处理:  {speed.get('preprocess', 0):.1f} ms/image")
            print(f"  推理:    {speed.get('inference', 0):.1f} ms/image")
            print(f"  后处理:  {speed.get('postprocess', 0):.1f} ms/image")
            total_time = sum(speed.values())
            print(f"  总计:    {total_time:.1f} ms/image ({1000 / total_time:.1f} FPS)")

        # 打印结果保存位置
        if hasattr(results, "save_dir"):
            print(f"\n💾 结果保存至: {results.save_dir}")

    except Exception as e:
        print(f"\n❌ 评估失败: {e}")
        raise


if __name__ == "__main__":
    main()
