"""Auto-label images using an ONNX model and save YOLO-format .txt files.

Converts ONNX inference results (pixel-coordinate bboxes) to YOLO format:
  class_id  x_center  y_center  width  height   (all normalized 0-1)

Usage:
    uv run python scripts/auto_label_onnx.py \\
        --model models/stage_a_crack/best.onnx \\
        --images data/stage_a_crack/images/test \\
        --output /tmp/stage_b_labels \\
        --conf 0.30
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from vision_analysis_pro.core.inference.onnx_engine import ONNXInferenceEngine

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-label images with ONNX model")
    parser.add_argument(
        "--model",
        required=True,
        help="Path to the ONNX model file",
    )
    parser.add_argument(
        "--images",
        required=True,
        help="Directory containing input images",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for YOLO .txt label files",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.30,
        help="Confidence threshold for detections (default: 0.30)",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.45,
        help="NMS IoU threshold (default: 0.45)",
    )
    parser.add_argument(
        "--class-id",
        type=int,
        default=0,
        help="YOLO class id to assign to all detections (default: 0)",
    )
    return parser.parse_args()


def bbox_to_yolo(
    x1: float, y1: float, x2: float, y2: float, img_w: int, img_h: int
) -> tuple[float, float, float, float]:
    """Convert pixel [x1,y1,x2,y2] to normalized YOLO [cx,cy,w,h]."""
    cx = (x1 + x2) / 2.0 / img_w
    cy = (y1 + y2) / 2.0 / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return (
        max(0.0, min(1.0, cx)),
        max(0.0, min(1.0, cy)),
        max(0.0, min(1.0, w)),
        max(0.0, min(1.0, h)),
    )


def main() -> None:
    args = parse_args()

    images_dir = Path(args.images)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(
        p for p in images_dir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not image_paths:
        print(f"[auto_label] 在 {images_dir} 中未找到图像文件")
        return

    print(f"[auto_label] 加载 ONNX 模型: {args.model}")
    engine = ONNXInferenceEngine(model_path=args.model)

    n_positive = 0
    n_empty = 0
    n_total_boxes = 0

    for img_path in image_paths:
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"  [跳过] 无法读取: {img_path.name}")
            continue

        img_h, img_w = img.shape[:2]
        detections = engine.predict(img, conf=args.conf, iou=args.iou)

        label_path = output_dir / (img_path.stem + ".txt")
        lines: list[str] = []
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cx, cy, bw, bh = bbox_to_yolo(x1, y1, x2, y2, img_w, img_h)
            lines.append(f"{args.class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

        label_path.write_text("\n".join(lines))

        if lines:
            n_positive += 1
            n_total_boxes += len(lines)
        else:
            n_empty += 1

    print(
        f"\n[auto_label] 完成 {len(image_paths)} 张图像自动标注"
        f"\n  有检测框: {n_positive} 张，共 {n_total_boxes} 个框"
        f"\n  空标签:   {n_empty} 张（无检测，保留为负样本）"
        f"\n  输出目录: {output_dir}"
    )


if __name__ == "__main__":
    main()
