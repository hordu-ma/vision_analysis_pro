"""数据集验证脚本

验证 YOLO 数据集的完整性和正确性：
- 检查 data.yaml 配置
- 验证图像与标注文件匹配
- 统计数据集信息
- 检查标注格式正确性
"""

from collections import Counter
from pathlib import Path

import yaml

# 类别定义（与 categories.py 和 data.yaml 保持一致）
EXPECTED_CATEGORIES = {
    0: "crack",
    1: "rust",
    2: "deformation",
    3: "spalling",
    4: "corrosion",
}


def load_data_config(yaml_path: Path) -> dict:
    """加载 data.yaml 配置"""
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    return config


def validate_config(config: dict) -> bool:
    """验证配置文件格式"""
    print("🔍 验证 data.yaml 配置...")

    # 必需字段
    required_fields = ["path", "train", "val", "nc", "names"]
    for field in required_fields:
        if field not in config:
            print(f"  ❌ 缺少必需字段: {field}")
            return False

    # 验证类别数量
    if config["nc"] != 5:
        print(f"  ❌ 类别数量错误: 期望 5, 实际 {config['nc']}")
        return False

    # 验证类别名称
    names = config["names"]
    if len(names) != 5:
        print(f"  ❌ 类别名称数量错误: 期望 5, 实际 {len(names)}")
        return False

    for idx, expected_name in EXPECTED_CATEGORIES.items():
        if names[idx] != expected_name:
            print(
                f"  ❌ 类别 {idx} 名称错误: 期望 '{expected_name}', 实际 '{names[idx]}'"
            )
            return False

    print("  ✅ 配置文件格式正确")
    return True


def check_dataset_split(
    data_root: Path, split: str
) -> tuple[list[Path], list[Path], dict]:
    """检查单个数据集切分

    Returns:
        (图像列表, 标注列表, 统计信息)
    """
    img_dir = data_root / "images" / split
    label_dir = data_root / "labels" / split

    print(f"\n📂 检查 {split} 集合...")
    print(f"  图像目录: {img_dir}")
    print(f"  标注目录: {label_dir}")

    # 检查目录是否存在
    if not img_dir.exists():
        print(f"  ❌ 图像目录不存在: {img_dir}")
        return [], [], {}
    if not label_dir.exists():
        print(f"  ❌ 标注目录不存在: {label_dir}")
        return [], [], {}

    # 收集图像文件
    img_files = sorted(
        list(img_dir.glob("*.jpg"))
        + list(img_dir.glob("*.png"))
        + list(img_dir.glob("*.jpeg"))
    )
    print(f"  找到 {len(img_files)} 张图像")

    # 收集标注文件
    label_files = sorted(list(label_dir.glob("*.txt")))
    print(f"  找到 {len(label_files)} 个标注文件")

    # 检查图像与标注匹配
    matched = 0
    unmatched_images = []
    unmatched_labels = []

    img_stems = {img.stem for img in img_files}
    label_stems = {label.stem for label in label_files}

    for img in img_files:
        if img.stem not in label_stems:
            unmatched_images.append(img.name)
        else:
            matched += 1

    for label in label_files:
        if label.stem not in img_stems:
            unmatched_labels.append(label.name)

    print(f"  ✅ 匹配: {matched} 对")

    if unmatched_images:
        print(f"  ⚠️  缺少标注的图像: {', '.join(unmatched_images[:5])}")
        if len(unmatched_images) > 5:
            print(f"     ... 还有 {len(unmatched_images) - 5} 个")

    if unmatched_labels:
        print(f"  ⚠️  缺少图像的标注: {', '.join(unmatched_labels[:5])}")
        if len(unmatched_labels) > 5:
            print(f"     ... 还有 {len(unmatched_labels) - 5} 个")

    # 统计标注信息
    stats = validate_annotations(label_files)

    return img_files, label_files, stats


def validate_annotations(label_files: list[Path]) -> dict:
    """验证标注文件格式并统计

    Returns:
        统计信息字典
    """
    total_objects = 0
    class_counter = Counter()
    invalid_files = []

    for label_file in label_files:
        try:
            with open(label_file) as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) != 5:
                    invalid_files.append(
                        f"{label_file.name}:{line_num} (字段数={len(parts)})"
                    )
                    continue

                class_id = int(parts[0])
                cx, cy, w, h = map(float, parts[1:])

                # 验证类别 ID
                if class_id not in EXPECTED_CATEGORIES:
                    invalid_files.append(
                        f"{label_file.name}:{line_num} (class_id={class_id} 无效)"
                    )
                    continue

                # 验证坐标范围
                if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < w <= 1 and 0 < h <= 1):
                    invalid_files.append(
                        f"{label_file.name}:{line_num} (坐标超出 [0,1] 范围)"
                    )
                    continue

                total_objects += 1
                class_counter[class_id] += 1

        except Exception as e:
            invalid_files.append(f"{label_file.name} (读取错误: {e})")

    if invalid_files:
        print(f"\n  ⚠️  发现 {len(invalid_files)} 个标注错误:")
        for err in invalid_files[:5]:
            print(f"     - {err}")
        if len(invalid_files) > 5:
            print(f"     ... 还有 {len(invalid_files) - 5} 个")

    return {
        "total_objects": total_objects,
        "class_distribution": dict(class_counter),
        "invalid_count": len(invalid_files),
    }


def print_summary(all_stats: dict) -> None:
    """打印数据集总结"""
    print("\n" + "=" * 60)
    print("📊 数据集统计总结")
    print("=" * 60)

    # 整体统计
    total_images = sum(s["image_count"] for s in all_stats.values())
    total_objects = sum(s["total_objects"] for s in all_stats.values())

    print(f"\n总图像数: {total_images}")
    print(f"总目标数: {total_objects}")
    print(f"平均每张图像目标数: {total_objects / total_images:.2f}")

    # 分集合统计
    print("\n各集合统计:")
    for split, stats in all_stats.items():
        print(
            f"  {split:6s}: {stats['image_count']:3d} 张图像, "
            f"{stats['total_objects']:3d} 个目标"
        )

    # 类别分布
    print("\n类别分布:")
    all_class_dist = Counter()
    for stats in all_stats.values():
        all_class_dist.update(stats["class_distribution"])

    for class_id, class_name in EXPECTED_CATEGORIES.items():
        count = all_class_dist.get(class_id, 0)
        percentage = (count / total_objects * 100) if total_objects > 0 else 0
        print(f"  {class_id} {class_name:12s}: {count:3d} ({percentage:5.2f}%)")

    # 验证结果
    print("\n验证结果:")
    total_invalid = sum(s["invalid_count"] for s in all_stats.values())
    if total_invalid == 0:
        print("  ✅ 所有标注格式正确")
    else:
        print(f"  ⚠️  发现 {total_invalid} 个标注错误，请检查")

    print("=" * 60)


def main() -> None:
    """主函数"""
    # 数据集根目录
    script_dir = Path(__file__).parent
    data_root = script_dir.parent / "data"
    yaml_path = data_root / "data.yaml"

    print("🚀 YOLO 数据集验证工具")
    print(f"📂 数据集根目录: {data_root}")
    print(f"📄 配置文件: {yaml_path}")

    # 1. 加载并验证配置
    if not yaml_path.exists():
        print(f"\n❌ 配置文件不存在: {yaml_path}")
        return

    config = load_data_config(yaml_path)
    if not validate_config(config):
        print("\n❌ 配置文件验证失败，请检查 data.yaml")
        return

    # 2. 检查各数据集切分
    all_stats = {}
    for split in ["train", "val", "test"]:
        img_files, label_files, stats = check_dataset_split(data_root, split)
        all_stats[split] = {
            "image_count": len(img_files),
            "label_count": len(label_files),
            **stats,
        }

    # 3. 打印总结
    print_summary(all_stats)

    # 4. 检查是否有数据
    total_images = sum(s["image_count"] for s in all_stats.values())
    if total_images == 0:
        print(
            "\n⚠️  警告: 数据集为空，请运行 scripts/generate_test_data.py 生成测试数据"
        )
    else:
        print(f"\n✅ 数据集验证完成！共 {total_images} 张图像可用于训练。")


if __name__ == "__main__":
    main()
