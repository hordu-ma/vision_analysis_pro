"""YOLO 模型训练脚本

使用 Ultralytics YOLO API 训练基础设施缺陷检测模型。

使用方法:
    python scripts/train.py

训练参数可通过命令行参数调整，默认使用小规模配置快速验证。
"""

import argparse
from pathlib import Path

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="训练 YOLO 模型")

    # 模型配置
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        help="预训练模型路径 (yolov8n.pt, yolov8s.pt, yolov8m.pt 等)",
    )

    # 数据配置
    parser.add_argument(
        "--data",
        type=str,
        default="data/data.yaml",
        help="数据集配置文件路径",
    )

    # 训练参数
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="训练轮数（默认 10，快速验证用）",
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=8,
        help="批次大小",
    )

    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="输入图像尺寸",
    )

    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="训练设备 (cpu, 0, 0,1 等)",
    )

    # 输出配置
    parser.add_argument(
        "--project",
        type=str,
        default="runs/train",
        help="训练结果保存目录",
    )

    parser.add_argument(
        "--name",
        type=str,
        default="exp",
        help="实验名称",
    )

    # 可复现性
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子（确保可复现）",
    )

    # 其他配置
    parser.add_argument(
        "--exist-ok",
        action="store_true",
        help="是否覆盖已存在的实验目录",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="数据加载线程数",
    )

    parser.add_argument(
        "--patience",
        type=int,
        default=5,
        help="早停耐心值（多少个 epoch 无改善则停止）",
    )

    return parser.parse_args()


def main() -> None:
    """主训练函数"""
    args = parse_args()

    print("=" * 60)
    print("🚀 YOLO 模型训练")
    print("=" * 60)

    # 打印配置
    print("\n📋 训练配置:")
    print(f"  预训练模型: {args.model}")
    print(f"  数据配置:   {args.data}")
    print(f"  训练轮数:   {args.epochs}")
    print(f"  批次大小:   {args.batch}")
    print(f"  图像尺寸:   {args.imgsz}")
    print(f"  训练设备:   {args.device}")
    print(f"  随机种子:   {args.seed}")
    print(f"  输出目录:   {args.project}/{args.name}")

    # 检查数据配置文件
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"\n❌ 错误: 数据配置文件不存在: {data_path}")
        print("   请先运行 scripts/generate_test_data.py 生成测试数据")
        return

    print("\n" + "=" * 60)
    print("🏋️  开始训练...")
    print("=" * 60 + "\n")

    # 加载模型
    model = YOLO(args.model)

    # 开始训练
    try:
        results = model.train(
            data=args.data,
            epochs=args.epochs,
            batch=args.batch,
            imgsz=args.imgsz,
            device=args.device,
            project=args.project,
            name=args.name,
            exist_ok=args.exist_ok,
            workers=args.workers,
            patience=args.patience,
            seed=args.seed,
            # 训练优化参数
            optimizer="Adam",  # 优化器
            lr0=0.001,  # 初始学习率
            lrf=0.01,  # 最终学习率（相对于 lr0）
            momentum=0.937,  # SGD 动量/Adam beta1
            weight_decay=0.0005,  # 权重衰减
            warmup_epochs=3.0,  # 预热轮数
            warmup_momentum=0.8,  # 预热动量
            # 数据增强
            hsv_h=0.015,  # HSV 色调增强
            hsv_s=0.7,  # HSV 饱和度增强
            hsv_v=0.4,  # HSV 明度增强
            degrees=0.0,  # 旋转角度
            translate=0.1,  # 平移
            scale=0.5,  # 缩放
            shear=0.0,  # 剪切
            perspective=0.0,  # 透视变换
            flipud=0.0,  # 上下翻转概率
            fliplr=0.5,  # 左右翻转概率
            mosaic=1.0,  # mosaic 增强概率
            mixup=0.0,  # mixup 增强概率
            # 保存配置
            save=True,  # 保存检查点
            save_period=-1,  # 每 N 个 epoch 保存一次（-1 表示仅保存最后）
            # 验证配置
            val=True,  # 每个 epoch 后验证
            plots=True,  # 保存训练图表
            # 日志
            verbose=True,  # 详细输出
        )

        print("\n" + "=" * 60)
        print("✅ 训练完成！")
        print("=" * 60)

        # 打印训练结果
        print("\n📊 训练结果:")
        print(f"  最佳模型: {results.save_dir}/weights/best.pt")
        print(f"  最终模型: {results.save_dir}/weights/last.pt")
        print(f"  结果目录: {results.save_dir}")

        # 打印性能指标
        if hasattr(results, "results_dict"):
            metrics = results.results_dict
            print("\n📈 性能指标:")
            print(f"  mAP50:     {metrics.get('metrics/mAP50(B)', 0):.4f}")
            print(f"  mAP50-95:  {metrics.get('metrics/mAP50-95(B)', 0):.4f}")
            print(f"  Precision: {metrics.get('metrics/precision(B)', 0):.4f}")
            print(f"  Recall:    {metrics.get('metrics/recall(B)', 0):.4f}")

    except Exception as e:
        print(f"\n❌ 训练失败: {e}")
        raise


if __name__ == "__main__":
    main()
