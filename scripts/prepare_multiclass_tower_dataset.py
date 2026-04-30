"""Prepare a YOLO dataset from the local multiclass tower-defect inbox."""

from __future__ import annotations

import argparse
import json
import random
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import cv2

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
SPLITS = ("train", "val", "test")

CLASSES = {
    0: "deformation",
    1: "tower_corrosion",
    2: "loose_bolt",
    3: "bolt_rust",
}


@dataclass(frozen=True)
class InboxCandidate:
    """One reviewed inbox image and its YOLO label file."""

    image_path: Path
    label_path: Path
    class_id: int


@dataclass(frozen=True)
class PreparedDataset:
    """Prepared multiclass dataset summary."""

    output: Path
    total_images: int
    total_boxes: int
    split_counts: dict[str, int]
    class_counts: dict[str, int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a multiclass tower-defect YOLO dataset",
    )
    parser.add_argument(
        "--inbox",
        default="data/multiclass_inbox",
        help="Local reviewed multiclass inbox directory",
    )
    parser.add_argument(
        "--output",
        default="data/multiclass_tower_defect",
        help="Output YOLO dataset directory",
    )
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate an existing output dataset",
    )
    return parser.parse_args()


def prepare_dataset(
    inbox: Path,
    output: Path,
    *,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> PreparedDataset:
    """Prepare a YOLO dataset from reviewed multiclass inbox labels."""
    _validate_ratios(train_ratio, val_ratio, test_ratio)
    candidates = collect_candidates(inbox)
    if not candidates:
        raise ValueError(f"no reviewed images found in inbox: {inbox}")

    _reset_output(output)
    _prepare_output_dirs(output)
    split_map = split_candidates(
        candidates,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        seed=seed,
    )

    total_boxes = 0
    class_counts = dict.fromkeys(CLASSES.values(), 0)
    copied_items: list[dict[str, object]] = []

    for split, split_candidates_ in split_map.items():
        for candidate in split_candidates_:
            image_target = output / "images" / split / candidate.image_path.name
            label_target = output / "labels" / split / candidate.label_path.name
            shutil.copy2(candidate.image_path, image_target)
            shutil.copy2(candidate.label_path, label_target)

            label_lines = _label_lines(candidate.label_path)
            total_boxes += len(label_lines)
            for line in label_lines:
                class_id = int(line.split()[0])
                class_counts[CLASSES[class_id]] += 1

            copied_items.append(
                {
                    "split": split,
                    "image": str(image_target),
                    "label": str(label_target),
                    "source_image": str(candidate.image_path),
                    "source_label": str(candidate.label_path),
                    "proposed_class_id": candidate.class_id,
                    "proposed_class_name": CLASSES[candidate.class_id],
                    "boxes": len(label_lines),
                }
            )

    write_data_yaml(output)
    split_counts = {split: len(items) for split, items in split_map.items()}
    write_manifest(
        output,
        inbox=inbox,
        split_counts=split_counts,
        class_counts=class_counts,
        total_boxes=total_boxes,
        items=copied_items,
        settings={
            "train_ratio": train_ratio,
            "val_ratio": val_ratio,
            "test_ratio": test_ratio,
            "seed": seed,
        },
    )
    validate_prepared_dataset(output)
    return PreparedDataset(
        output=output,
        total_images=len(candidates),
        total_boxes=total_boxes,
        split_counts=split_counts,
        class_counts=class_counts,
    )


def collect_candidates(inbox: Path) -> list[InboxCandidate]:
    """Collect reviewed image/label pairs from the local inbox."""
    raw_images = inbox / "raw_images"
    reviewed_labels = inbox / "reviewed_labels"
    metadata_dir = inbox / "metadata"
    if not raw_images.exists():
        raise FileNotFoundError(f"missing raw_images directory: {raw_images}")
    if not reviewed_labels.exists():
        raise FileNotFoundError(f"missing reviewed_labels directory: {reviewed_labels}")

    candidates: list[InboxCandidate] = []
    for image_path in sorted(raw_images.iterdir()):
        if (
            not image_path.is_file()
            or image_path.suffix.lower() not in IMAGE_EXTENSIONS
        ):
            continue
        validate_image_file(image_path)
        label_path = reviewed_labels / f"{image_path.stem}.txt"
        if not label_path.exists():
            raise FileNotFoundError(f"missing reviewed label for {image_path}")
        validate_label_file(label_path)
        metadata_path = metadata_dir / f"{image_path.stem}.json"
        class_id = _class_id_from_metadata_or_label(metadata_path, label_path)
        candidates.append(
            InboxCandidate(
                image_path=image_path,
                label_path=label_path,
                class_id=class_id,
            )
        )

    label_stems = {path.stem for path in reviewed_labels.glob("*.txt")}
    image_stems = {
        path.stem
        for path in raw_images.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    }
    orphan_labels = label_stems - image_stems
    if orphan_labels:
        raise ValueError(f"reviewed labels without images: {sorted(orphan_labels)}")
    return candidates


def split_candidates(
    candidates: list[InboxCandidate],
    *,
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> dict[str, list[InboxCandidate]]:
    """Split candidates while keeping at least one validation image when possible."""
    shuffled = list(candidates)
    random.Random(seed).shuffle(shuffled)
    total = len(shuffled)
    train_count = int(total * train_ratio)
    val_count = int(total * val_ratio)
    if total >= 3:
        train_count = max(1, train_count)
        val_count = max(1, val_count)
    if train_count + val_count > total:
        val_count = max(0, total - train_count)
    test_count = total - train_count - val_count
    if total >= 3 and test_count == 0:
        if train_count > val_count and train_count > 1:
            train_count -= 1
        elif val_count > 1:
            val_count -= 1

    train_end = train_count
    val_end = train_end + val_count
    return {
        "train": shuffled[:train_end],
        "val": shuffled[train_end:val_end],
        "test": shuffled[val_end:],
    }


def validate_prepared_dataset(output: Path) -> None:
    """Validate image/label pairing and multiclass YOLO label format."""
    for split in SPLITS:
        image_dir = output / "images" / split
        label_dir = output / "labels" / split
        if not image_dir.exists() or not label_dir.exists():
            raise FileNotFoundError(f"missing split directories for {split}")

        image_stems = {path.stem for path in _iter_images(image_dir)}
        label_stems = {path.stem for path in label_dir.glob("*.txt")}
        missing_labels = image_stems - label_stems
        orphan_labels = label_stems - image_stems
        if missing_labels:
            raise ValueError(f"{split} images missing labels: {sorted(missing_labels)}")
        if orphan_labels:
            raise ValueError(f"{split} labels missing images: {sorted(orphan_labels)}")

        for image_path in _iter_images(image_dir):
            validate_image_file(image_path)
        for label_path in label_dir.glob("*.txt"):
            validate_label_file(label_path)


def validate_image_file(image_path: Path) -> None:
    """Validate that an image is readable by OpenCV."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"not a readable image: {image_path}")


def validate_label_file(label_path: Path) -> None:
    """Validate a multiclass YOLO label file."""
    lines = _label_lines(label_path)
    if not lines:
        raise ValueError(f"empty reviewed label file: {label_path}")
    for line_number, line in enumerate(lines, 1):
        parts = line.split()
        if len(parts) != 5:
            raise ValueError(f"{label_path}:{line_number} must contain 5 fields")
        try:
            class_id = int(parts[0])
            center_x, center_y, width, height = map(float, parts[1:])
        except ValueError as exc:
            raise ValueError(f"{label_path}:{line_number} has invalid values") from exc
        if class_id not in CLASSES:
            raise ValueError(f"{label_path}:{line_number} has invalid class {class_id}")
        if not (
            0 <= center_x <= 1
            and 0 <= center_y <= 1
            and 0 < width <= 1
            and 0 < height <= 1
        ):
            raise ValueError(f"{label_path}:{line_number} bbox values out of range")
        if (
            center_x - width / 2 < 0
            or center_y - height / 2 < 0
            or center_x + width / 2 > 1
            or center_y + height / 2 > 1
        ):
            raise ValueError(f"{label_path}:{line_number} bbox extends outside image")


def write_data_yaml(output: Path) -> None:
    """Write multiclass YOLO data.yaml."""
    names = "\n".join(f"  {class_id}: {name}" for class_id, name in CLASSES.items())
    content = (
        f"path: {output.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        f"nc: {len(CLASSES)}\n"
        "names:\n"
        f"{names}\n"
    )
    (output / "data.yaml").write_text(content, encoding="utf-8")


def write_manifest(
    output: Path,
    *,
    inbox: Path,
    split_counts: dict[str, int],
    class_counts: dict[str, int],
    total_boxes: int,
    items: list[dict[str, object]],
    settings: dict[str, object],
) -> None:
    """Write dataset preparation metadata."""
    manifest = {
        "inbox": str(inbox),
        "created_at": datetime.now(tz=UTC).isoformat(),
        "classes": CLASSES,
        "split_counts": split_counts,
        "class_counts": class_counts,
        "total_images": len(items),
        "total_boxes": total_boxes,
        "settings": settings,
        "items": items,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _class_id_from_metadata_or_label(metadata_path: Path, label_path: Path) -> int:
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        class_id = int(metadata["proposed_class_id"])
        if class_id not in CLASSES:
            raise ValueError(
                f"invalid proposed_class_id in {metadata_path}: {class_id}"
            )
        return class_id
    first_line = _label_lines(label_path)[0]
    class_id = int(first_line.split()[0])
    if class_id not in CLASSES:
        raise ValueError(f"invalid class id in {label_path}: {class_id}")
    return class_id


def _label_lines(label_path: Path) -> list[str]:
    return [
        line.strip()
        for line in label_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _iter_images(path: Path) -> list[Path]:
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def _validate_ratios(train_ratio: float, val_ratio: float, test_ratio: float) -> None:
    total = train_ratio + val_ratio + test_ratio
    if abs(total - 1.0) > 1e-6:
        raise ValueError("train/val/test ratios must sum to 1.0")
    if min(train_ratio, val_ratio, test_ratio) < 0:
        raise ValueError("train/val/test ratios must be non-negative")


def _reset_output(output: Path) -> None:
    for relative in ["images", "labels", "data.yaml", "manifest.json"]:
        target = output / relative
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def _prepare_output_dirs(output: Path) -> None:
    for split in SPLITS:
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    if args.validate_only:
        validate_prepared_dataset(output)
        print(f"dataset={output}")
        print("valid=true")
        return

    summary = prepare_dataset(
        Path(args.inbox),
        output,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )
    print(f"dataset={summary.output}")
    print(f"total_images={summary.total_images}")
    print(f"total_boxes={summary.total_boxes}")
    for split, count in summary.split_counts.items():
        print(f"{split}_images={count}")
    for class_name, count in summary.class_counts.items():
        print(f"{class_name}_boxes={count}")
    print("ready_for_smoke_training=true")


if __name__ == "__main__":
    main()
