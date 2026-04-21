"""Shared helpers for crack-only YOLO dataset preparation."""

from __future__ import annotations

from pathlib import Path

import cv2

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SPLITS = ("train", "val", "test")


def iter_images(path: Path) -> list[Path]:
    """Return supported image files directly under one directory."""
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def validate_image_file(image_path: Path) -> None:
    """Validate that a dataset image is readable by OpenCV."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"{image_path} is not a readable image")


def validate_label_lines(lines: list[str], *, source_name: str) -> None:
    """Validate crack-only YOLO label lines before writing them."""
    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != 5:
            raise ValueError(f"{source_name}:{line_number} must contain 5 fields")
        class_id = int(parts[0])
        if class_id != 0:
            raise ValueError(f"{source_name}:{line_number} only class id 0 is allowed")
        center_x, center_y, width, height = map(float, parts[1:])
        if not (
            0 <= center_x <= 1
            and 0 <= center_y <= 1
            and 0 < width <= 1
            and 0 < height <= 1
        ):
            raise ValueError(f"{source_name}:{line_number} bbox values out of range")


def validate_label_file(label_path: Path) -> None:
    """Validate one crack-only YOLO label file."""
    validate_label_lines(
        label_path.read_text(encoding="utf-8").splitlines(),
        source_name=str(label_path),
    )


def validate_prepared_dataset(output: Path) -> None:
    """Validate image/label pairing and YOLO label format."""
    for split in SPLITS:
        image_dir = output / "images" / split
        label_dir = output / "labels" / split
        if not image_dir.exists() or not label_dir.exists():
            raise FileNotFoundError(f"missing split directories for {split}")

        image_stems = {path.stem for path in iter_images(image_dir)}
        label_stems = {path.stem for path in label_dir.glob("*.txt")}
        missing_labels = image_stems - label_stems
        orphan_labels = label_stems - image_stems
        if missing_labels:
            raise ValueError(f"{split} images missing labels: {sorted(missing_labels)}")
        if orphan_labels:
            raise ValueError(f"{split} labels missing images: {sorted(orphan_labels)}")

        for image_path in iter_images(image_dir):
            validate_image_file(image_path)

        for label_path in label_dir.glob("*.txt"):
            validate_label_file(label_path)


def write_crack_data_yaml(output: Path) -> None:
    """Write crack-only YOLO data.yaml."""
    content = (
        f"path: {output.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        "nc: 1\n"
        "names:\n"
        "  0: crack\n"
    )
    (output / "data.yaml").write_text(content, encoding="utf-8")
