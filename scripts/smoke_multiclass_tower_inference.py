"""Run a local inference smoke for the multiclass tower-defect prototype."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2

from vision_analysis_pro.core.inference import YOLOInferenceEngine

DEFAULT_MODEL_PATH = "runs/multiclass_tower_defect/smoke_v0_1/weights/best.pt"
DEFAULT_IMAGE_DIR = "data/multiclass_tower_defect/images/test"
DEFAULT_OUTPUT = "data/multiclass_tower_defect/inference_smoke/results.json"

EXPECTED_CLASSES = {
    0: "deformation",
    1: "tower_corrosion",
    2: "loose_bolt",
    3: "bolt_rust",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run multiclass tower-defect inference smoke",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--images", default=DEFAULT_IMAGE_DIR)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--preview-dir",
        default="data/multiclass_tower_defect/inference_smoke/previews",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.001,
        help="Low default is intentional for 1-epoch smoke weights",
    )
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument(
        "--max-images",
        type=int,
        default=None,
        help="Optional maximum number of images to process",
    )
    return parser.parse_args()


def run_smoke(
    model_path: Path,
    image_dir: Path,
    output_path: Path,
    *,
    preview_dir: Path | None = None,
    conf: float = 0.001,
    iou: float = 0.5,
    max_images: int | None = None,
) -> dict[str, Any]:
    """Run YOLO inference smoke and write a JSON summary."""
    image_paths = _iter_images(image_dir)
    if max_images is not None:
        image_paths = image_paths[:max_images]
    if not image_paths:
        raise ValueError(f"no supported images found under: {image_dir}")

    engine = YOLOInferenceEngine(model_path)
    _validate_class_names(engine.class_names)

    results: list[dict[str, Any]] = []
    for image_path in image_paths:
        detections = engine.predict(image_path, conf=conf, iou=iou)
        results.append(
            {
                "image": str(image_path),
                "detections": detections,
                "detection_count": len(detections),
            }
        )
        if preview_dir is not None:
            _write_preview(image_path, detections, preview_dir / image_path.name)

    total_detections = sum(item["detection_count"] for item in results)
    summary = {
        "model": str(model_path),
        "images": str(image_dir),
        "created_at": datetime.now(tz=UTC).isoformat(),
        "conf": conf,
        "iou": iou,
        "class_names": engine.class_names,
        "total_images": len(results),
        "total_detections": total_detections,
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def _iter_images(image_dir: Path) -> list[Path]:
    if not image_dir.exists():
        raise FileNotFoundError(f"image directory does not exist: {image_dir}")
    return sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def _validate_class_names(class_names: dict[int, str]) -> None:
    normalized = {int(key): value for key, value in class_names.items()}
    for class_id, expected_name in EXPECTED_CLASSES.items():
        actual_name = normalized.get(class_id)
        if actual_name != expected_name:
            raise ValueError(
                "unexpected model class mapping: "
                f"class {class_id} expected {expected_name!r}, got {actual_name!r}"
            )


def _write_preview(
    image_path: Path,
    detections: list[dict[str, Any]],
    output_path: Path,
) -> None:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"not a readable image: {image_path}")
    for detection in detections:
        x1, y1, x2, y2 = [int(value) for value in detection["bbox"]]
        label = detection["label"]
        confidence = detection["confidence"]
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 220, 0), 2)
        cv2.putText(
            image,
            f"{label} {confidence:.2f}",
            (x1, max(24, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 220, 0),
            2,
            cv2.LINE_AA,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), image)


def main() -> None:
    args = parse_args()
    summary = run_smoke(
        Path(args.model),
        Path(args.images),
        Path(args.output),
        preview_dir=Path(args.preview_dir),
        conf=args.conf,
        iou=args.iou,
        max_images=args.max_images,
    )
    print(f"model={summary['model']}")
    print(f"images={summary['total_images']}")
    print(f"detections={summary['total_detections']}")
    print(f"output={args.output}")
    print(f"preview_dir={args.preview_dir}")


if __name__ == "__main__":
    main()
