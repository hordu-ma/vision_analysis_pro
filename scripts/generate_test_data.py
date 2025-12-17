"""生成测试数据集

为 YOLO 训练创建小规模测试数据集，包含合成图像和对应标注。
用于验证数据目录结构和 data.yaml 配置。
"""

import random
from pathlib import Path

import cv2
import numpy as np

# 类别定义（与 categories.py 保持一致）
CATEGORIES = {
    0: "crack",
    1: "rust",
    2: "deformation",
    3: "spalling",
    4: "corrosion",
}

# BGR 颜色（用于绘制不同类别的缺陷）
COLORS = {
    0: (0, 0, 255),  # crack: 红色
    1: (0, 136, 255),  # rust: 橙色
    2: (0, 255, 255),  # deformation: 黄色
    3: (255, 0, 136),  # spalling: 紫色
    4: (255, 255, 0),  # corrosion: 青色
}


def create_synthetic_image(
    width: int = 640,
    height: int = 480,
    num_objects: int = 3,
    class_id: int | None = None,
) -> tuple[np.ndarray, list[tuple[int, float, float, float, float]]]:
    """创建合成图像和对应的标注

    Args:
        width: 图像宽度
        height: 图像高度
        num_objects: 目标数量
        class_id: 指定类别ID，None 则随机

    Returns:
        (图像, 标注列表)，标注格式为 (class_id, cx, cy, w, h)
    """
    # 创建灰色背景（模拟混凝土/金属表面）
    img = np.ones((height, width, 3), dtype=np.uint8) * 120
    img += np.random.randint(-20, 20, (height, width, 3), dtype=np.int16).astype(
        np.uint8
    )

    annotations = []

    for _ in range(num_objects):
        # 随机选择类别
        cid = class_id if class_id is not None else random.randint(0, 4)
        color = COLORS[cid]

        # 随机生成 bbox（归一化坐标）
        cx = random.uniform(0.15, 0.85)
        cy = random.uniform(0.15, 0.85)
        w = random.uniform(0.05, 0.25)
        h = random.uniform(0.05, 0.25)

        # 转换为像素坐标
        x1 = int((cx - w / 2) * width)
        y1 = int((cy - h / 2) * height)
        x2 = int((cx + w / 2) * width)
        y2 = int((cy + h / 2) * height)

        # 绘制模拟缺陷
        if cid == 0:  # crack - 裂缝（线条）
            cv2.line(img, (x1, y1), (x2, y2), color, thickness=random.randint(2, 5))
            # 添加一些分支
            mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.line(
                img,
                (mid_x, mid_y),
                (mid_x + random.randint(-30, 30), mid_y + random.randint(-30, 30)),
                color,
                thickness=2,
            )
        elif cid == 1:  # rust - 锈蚀（斑块）
            cv2.ellipse(
                img,
                ((x1 + x2) // 2, (y1 + y2) // 2),
                ((x2 - x1) // 2, (y2 - y1) // 2),
                0,
                0,
                360,
                color,
                -1,
            )
        elif cid == 2:  # deformation - 变形（曲线）
            pts = np.array(
                [
                    [x1, (y1 + y2) // 2],
                    [(x1 + x2) // 2, y1],
                    [x2, (y1 + y2) // 2],
                    [(x1 + x2) // 2, y2],
                ],
                np.int32,
            )
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(img, [pts], True, color, thickness=3)
        elif cid == 3:  # spalling - 剥落（不规则多边形）
            pts = np.array(
                [
                    [x1, y1],
                    [x2, y1],
                    [x2, y2],
                    [(x1 + x2) // 2, y2 + random.randint(-10, 10)],
                    [x1, y2],
                ],
                np.int32,
            )
            pts = pts.reshape((-1, 1, 2))
            cv2.fillPoly(img, [pts], color)
        else:  # corrosion - 腐蚀（点状坑洞）
            for _ in range(random.randint(5, 10)):
                px = random.randint(x1, x2)
                py = random.randint(y1, y2)
                cv2.circle(img, (px, py), random.randint(2, 5), color, -1)

        annotations.append((cid, cx, cy, w, h))

    return img, annotations


def generate_dataset(
    output_dir: Path,
    train_count: int = 6,
    val_count: int = 2,
    test_count: int = 2,
) -> None:
    """生成完整的测试数据集

    Args:
        output_dir: 输出根目录（data/）
        train_count: 训练集图像数量
        val_count: 验证集图像数量
        test_count: 测试集图像数量
    """
    splits = {
        "train": train_count,
        "val": val_count,
        "test": test_count,
    }

    random.seed(42)  # 固定随机种子确保可复现

    for split, count in splits.items():
        print(f"\n生成 {split} 集合...")

        img_dir = output_dir / "images" / split
        label_dir = output_dir / "labels" / split

        for i in range(count):
            # 为每个类别至少生成一张图像
            class_id = i % 5 if i < 5 else None

            # 生成图像和标注
            img, annotations = create_synthetic_image(
                width=640,
                height=480,
                num_objects=random.randint(1, 3),
                class_id=class_id,
            )

            # 保存图像
            img_filename = f"sample_{i:03d}.jpg"
            img_path = img_dir / img_filename
            cv2.imwrite(str(img_path), img)

            # 保存标注
            label_filename = f"sample_{i:03d}.txt"
            label_path = label_dir / label_filename

            with open(label_path, "w") as f:
                for cid, cx, cy, w, h in annotations:
                    # YOLO 格式：class_id center_x center_y width height
                    f.write(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

            print(
                f"  - {img_filename}: {len(annotations)} 个目标 "
                f"({', '.join(CATEGORIES[ann[0]] for ann in annotations)})"
            )

    print("\n✅ 数据集生成完成！")
    print(f"  训练集: {train_count} 张")
    print(f"  验证集: {val_count} 张")
    print(f"  测试集: {test_count} 张")
    print(f"  总计: {train_count + val_count + test_count} 张")


if __name__ == "__main__":
    # 数据集根目录
    data_root = Path(__file__).parent.parent / "data"

    # 生成数据集
    generate_dataset(
        output_dir=data_root,
        train_count=6,  # 训练集 6 张（每个类别至少 1 张）
        val_count=2,  # 验证集 2 张
        test_count=2,  # 测试集 2 张
    )

    print(f"\n📂 数据集位置: {data_root}")
    print("📝 下一步: 运行 scripts/validate_data.py 验证数据集")
