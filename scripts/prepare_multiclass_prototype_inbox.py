"""Prepare the local multiclass tower-defect prototype inbox."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import cv2

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

CLASS_MAPPING = {
    "变形": (0, "deformation"),
    "塔材腐蚀": (1, "tower_corrosion"),
    "螺栓松动": (2, "loose_bolt"),
    "螺栓锈蚀": (3, "bolt_rust"),
}


@dataclass(frozen=True)
class InboxItem:
    """One source image copied into the prototype annotation inbox."""

    source_path: Path
    image_path: Path
    metadata_path: Path
    proposed_class_id: int
    proposed_class_name: str
    width: int
    height: int


@dataclass(frozen=True)
class InboxSummary:
    """Prepared inbox summary."""

    output: Path
    total_images: int
    class_counts: dict[str, int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a local multiclass tower-defect prototype inbox",
    )
    parser.add_argument(
        "--source",
        default="/home/liguoma/Downloads/锈蚀、松动、变形、腐蚀",
        help="Source directory with one subdirectory per defect class",
    )
    parser.add_argument(
        "--output",
        default="data/multiclass_inbox",
        help="Ignored local inbox output directory",
    )
    parser.add_argument(
        "--site-name",
        default="tower-defect-downloads",
        help="Default site_name written to metadata files",
    )
    parser.add_argument(
        "--device-id",
        default="downloads-import",
        help="Default device_id written to metadata files",
    )
    parser.add_argument(
        "--asset-prefix",
        default="tower-defect",
        help="Default asset_id prefix written to metadata files",
    )
    return parser.parse_args()


def prepare_inbox(
    source: Path,
    output: Path,
    *,
    site_name: str = "tower-defect-downloads",
    device_id: str = "downloads-import",
    asset_prefix: str = "tower-defect",
) -> InboxSummary:
    """Copy source images into a local annotation inbox and write metadata."""
    if not source.exists():
        raise FileNotFoundError(f"source directory does not exist: {source}")
    if not source.is_dir():
        raise NotADirectoryError(f"source is not a directory: {source}")

    raw_images = output / "raw_images"
    metadata_dir = output / "metadata"
    reviewed_labels = output / "reviewed_labels"
    raw_images.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    reviewed_labels.mkdir(parents=True, exist_ok=True)

    items: list[InboxItem] = []
    for class_dir_name, (class_id, class_name) in CLASS_MAPPING.items():
        class_dir = source / class_dir_name
        if not class_dir.exists():
            continue
        for index, image_source in enumerate(_iter_images(class_dir), start=1):
            image = cv2.imread(str(image_source))
            if image is None:
                raise ValueError(f"not a readable image: {image_source}")
            height, width = image.shape[:2]
            target_stem = f"{class_name}_{index:03d}"
            image_target = raw_images / f"{target_stem}{image_source.suffix.lower()}"
            metadata_target = metadata_dir / f"{target_stem}.json"
            shutil.copy2(image_source, image_target)

            metadata = {
                "asset_id": f"{asset_prefix}-{class_name}-{index:03d}",
                "device_id": device_id,
                "site_name": site_name,
                "capture_time": _capture_time(image_source),
                "source_type": "manual_download",
                "source_path": str(image_source),
                "proposed_class_id": class_id,
                "proposed_class_name": class_name,
                "review_status": "pending_bbox_annotation",
                "reviewer": "",
                "review_rule_version": "",
                "width": width,
                "height": height,
            }
            metadata_target.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            items.append(
                InboxItem(
                    source_path=image_source,
                    image_path=image_target,
                    metadata_path=metadata_target,
                    proposed_class_id=class_id,
                    proposed_class_name=class_name,
                    width=width,
                    height=height,
                )
            )

    if not items:
        raise ValueError(f"no supported images found under: {source}")

    _write_annotation_queue(output / "annotation_queue.csv", items)
    _write_class_mapping(output / "classes.json")
    _write_manifest(output / "manifest.json", source, items)

    class_counts = {
        class_name: sum(1 for item in items if item.proposed_class_name == class_name)
        for _, class_name in CLASS_MAPPING.values()
    }
    return InboxSummary(
        output=output,
        total_images=len(items),
        class_counts=class_counts,
    )


def _iter_images(path: Path) -> list[Path]:
    return sorted(
        child
        for child in path.iterdir()
        if child.is_file() and child.suffix.lower() in IMAGE_EXTENSIONS
    )


def _capture_time(path: Path) -> str:
    timestamp = path.stat().st_mtime
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _write_annotation_queue(path: Path, items: list[InboxItem]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image",
                "metadata",
                "label",
                "proposed_class_id",
                "proposed_class_name",
                "width",
                "height",
                "source_path",
                "annotation_status",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(
                {
                    "image": item.image_path,
                    "metadata": item.metadata_path,
                    "label": path.parent
                    / "reviewed_labels"
                    / f"{item.image_path.stem}.txt",
                    "proposed_class_id": item.proposed_class_id,
                    "proposed_class_name": item.proposed_class_name,
                    "width": item.width,
                    "height": item.height,
                    "source_path": item.source_path,
                    "annotation_status": "pending_bbox_annotation",
                }
            )


def _write_class_mapping(path: Path) -> None:
    classes = [
        {"id": class_id, "name": class_name, "source_folder": source_folder}
        for source_folder, (class_id, class_name) in CLASS_MAPPING.items()
    ]
    path.write_text(
        json.dumps({"classes": classes}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_manifest(path: Path, source: Path, items: list[InboxItem]) -> None:
    manifest = {
        "source": str(source),
        "created_at": datetime.now(tz=UTC).isoformat(),
        "total_images": len(items),
        "class_counts": {
            class_name: sum(
                1 for item in items if item.proposed_class_name == class_name
            )
            for _, class_name in CLASS_MAPPING.values()
        },
        "annotation_status": "pending_bbox_annotation",
        "items": [
            {
                "image": str(item.image_path),
                "metadata": str(item.metadata_path),
                "source": str(item.source_path),
                "proposed_class_id": item.proposed_class_id,
                "proposed_class_name": item.proposed_class_name,
                "width": item.width,
                "height": item.height,
            }
            for item in items
        ],
    }
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    summary = prepare_inbox(
        Path(args.source),
        Path(args.output),
        site_name=args.site_name,
        device_id=args.device_id,
        asset_prefix=args.asset_prefix,
    )
    print(f"multiclass_inbox={summary.output}")
    print(f"total_images={summary.total_images}")
    for class_name, count in summary.class_counts.items():
        print(f"{class_name}={count}")
    print("ready_for_annotation=true")
    print("ready_for_training=false")


if __name__ == "__main__":
    main()
