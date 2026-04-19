"""Prepare a crack-only YOLO dataset for Stage A.

The default source is the public Hugging Face dataset
``senthilsk/crack_detection_dataset``. It is exported from Roboflow in COCO
format, so this script downloads/extracts the split archives, keeps crack-like
classes, converts boxes to YOLO format, and writes a standalone dataset under
``data/stage_a_crack``.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_REPO_ID = "senthilsk/crack_detection_dataset"
DEFAULT_CRACK_NAMES = ("crack", "stairstep_crack", "cracked")
DEFAULT_SPLITS = {
    "train": "train",
    "valid": "val",
    "test": "test",
}
DEFAULT_DOWNLOAD_FILES = (
    "README.md",
    "README.dataset.txt",
    "README.roboflow.txt",
    "data/train.zip",
    "data/valid.zip",
    "data/test.zip",
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass(frozen=True)
class SplitSummary:
    split: str
    images: int
    positives: int
    negatives: int
    objects: int
    skipped_objects: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the public crack dataset as a YOLO Stage A dataset."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/public/senthilsk_crack_detection_dataset"),
        help="Directory containing downloaded source files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/stage_a_crack"),
        help="Output YOLO dataset directory.",
    )
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help="Hugging Face dataset repo to download from.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the default public dataset files before conversion.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract archives and replace the output directory.",
    )
    parser.add_argument(
        "--crack-name",
        action="append",
        dest="crack_names",
        default=None,
        help="Source category name to map to target class crack. Can be repeated.",
    )
    parser.add_argument(
        "--negative-ratio",
        type=float,
        default=0.25,
        help="Maximum negative images per split as a ratio of positive images.",
    )
    parser.add_argument(
        "--no-negatives",
        action="store_true",
        help="Do not include empty-label negative images.",
    )
    return parser.parse_args()


def download_dataset_files(source: Path, repo_id: str, force: bool = False) -> None:
    source.mkdir(parents=True, exist_ok=True)
    base_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main"
    for file_name in DEFAULT_DOWNLOAD_FILES:
        target = source / file_name
        if target.exists() and not force:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        url = f"{base_url}/{file_name}"
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, target)  # noqa: S310


def extract_archives(source: Path, force: bool = False) -> Path:
    extract_root = source / "extracted"
    extract_root.mkdir(parents=True, exist_ok=True)

    for source_split in DEFAULT_SPLITS:
        target_dir = extract_root / source_split
        archive = find_split_archive(source, source_split)
        if not archive:
            continue
        if target_dir.exists() and force:
            shutil.rmtree(target_dir)
        if target_dir.exists() and any(target_dir.iterdir()):
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(target_dir)

    return extract_root


def find_split_archive(source: Path, split: str) -> Path | None:
    candidates = [
        source / "data" / f"{split}.zip",
        source / f"{split}.zip",
        source / f"data_{split}.zip",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = sorted(source.glob(f"**/{split}.zip"))
    return matches[0] if matches else None


def prepare_dataset(
    source: Path,
    output: Path,
    *,
    crack_names: set[str] | None = None,
    negative_ratio: float = 0.25,
    include_negatives: bool = True,
    force: bool = False,
) -> list[SplitSummary]:
    crack_names = {name.lower() for name in (crack_names or set(DEFAULT_CRACK_NAMES))}
    if force and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    extract_root = extract_archives(source, force=force)
    summaries: list[SplitSummary] = []
    for source_split, target_split in DEFAULT_SPLITS.items():
        split_dir = extract_root / source_split
        if not split_dir.exists():
            continue
        annotation_path = find_coco_annotation(split_dir)
        if not annotation_path:
            raise FileNotFoundError(f"COCO annotation file not found in {split_dir}")

        summary = convert_coco_split(
            annotation_path,
            split_dir,
            output,
            target_split,
            crack_names=crack_names,
            negative_ratio=negative_ratio,
            include_negatives=include_negatives,
        )
        summaries.append(summary)

    if not summaries:
        raise FileNotFoundError(f"No usable split archives found under {source}")

    write_data_yaml(output)
    write_manifest(output, summaries, crack_names)
    return summaries


def find_coco_annotation(split_dir: Path) -> Path | None:
    patterns = (
        "**/_annotations.coco.json",
        "**/*_annotations*.json",
        "**/*.coco.json",
        "**/annotations.json",
    )
    for pattern in patterns:
        matches = sorted(split_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def convert_coco_split(
    annotation_path: Path,
    split_dir: Path,
    output: Path,
    target_split: str,
    *,
    crack_names: set[str],
    negative_ratio: float,
    include_negatives: bool,
) -> SplitSummary:
    with annotation_path.open("r", encoding="utf-8") as f:
        coco = json.load(f)

    images = {int(image["id"]): image for image in coco.get("images", [])}
    category_by_id = {
        int(category["id"]): str(category["name"]).lower()
        for category in coco.get("categories", [])
    }
    target_category_ids = {
        category_id
        for category_id, category_name in category_by_id.items()
        if category_name in crack_names
    }

    annotations_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for annotation in coco.get("annotations", []):
        annotations_by_image[int(annotation["image_id"])].append(annotation)

    image_lookup = build_image_lookup(split_dir)
    image_dir = output / "images" / target_split
    label_dir = output / "labels" / target_split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    positives: list[tuple[dict[str, Any], list[str], int]] = []
    negatives: list[dict[str, Any]] = []
    skipped_objects = 0

    for image in sorted(images.values(), key=lambda item: str(item.get("file_name", ""))):
        yolo_lines: list[str] = []
        skipped_for_image = 0
        for annotation in annotations_by_image.get(int(image["id"]), []):
            if int(annotation.get("category_id", -1)) not in target_category_ids:
                continue
            line = coco_box_to_yolo_line(annotation, image)
            if line is None:
                skipped_for_image += 1
                continue
            yolo_lines.append(line)

        if yolo_lines:
            positives.append((image, yolo_lines, skipped_for_image))
        else:
            negatives.append(image)
            skipped_objects += skipped_for_image

    selected_negatives: list[dict[str, Any]] = []
    if include_negatives and negative_ratio > 0:
        negative_limit = math.ceil(len(positives) * negative_ratio)
        selected_negatives = negatives[:negative_limit]

    written_names: set[str] = set()
    object_count = 0
    for image, lines, skipped_for_image in positives:
        object_count += len(lines)
        skipped_objects += skipped_for_image
        copy_image_and_write_label(
            image,
            lines,
            image_lookup,
            image_dir,
            label_dir,
            written_names,
        )

    for image in selected_negatives:
        copy_image_and_write_label(
            image,
            [],
            image_lookup,
            image_dir,
            label_dir,
            written_names,
        )

    return SplitSummary(
        split=target_split,
        images=len(positives) + len(selected_negatives),
        positives=len(positives),
        negatives=len(selected_negatives),
        objects=object_count,
        skipped_objects=skipped_objects,
    )


def build_image_lookup(split_dir: Path) -> dict[str, Path]:
    lookup: dict[str, Path] = {}
    for image_path in split_dir.rglob("*"):
        if image_path.is_file() and image_path.suffix.lower() in IMAGE_SUFFIXES:
            lookup.setdefault(image_path.name, image_path)
            relative = image_path.relative_to(split_dir).as_posix()
            lookup.setdefault(relative, image_path)
    return lookup


def coco_box_to_yolo_line(annotation: dict[str, Any], image: dict[str, Any]) -> str | None:
    bbox = annotation.get("bbox")
    if not bbox or len(bbox) != 4:
        return None

    image_width = float(image.get("width") or 0)
    image_height = float(image.get("height") or 0)
    if image_width <= 0 or image_height <= 0:
        return None

    x, y, width, height = map(float, bbox)
    x = max(0.0, x)
    y = max(0.0, y)
    width = min(width, image_width - x)
    height = min(height, image_height - y)
    if width <= 0 or height <= 0:
        return None

    cx = (x + width / 2.0) / image_width
    cy = (y + height / 2.0) / image_height
    norm_width = width / image_width
    norm_height = height / image_height
    return f"0 {cx:.6f} {cy:.6f} {norm_width:.6f} {norm_height:.6f}"


def copy_image_and_write_label(
    image: dict[str, Any],
    lines: list[str],
    image_lookup: dict[str, Path],
    image_dir: Path,
    label_dir: Path,
    written_names: set[str],
) -> None:
    file_name = str(image["file_name"])
    source_image = image_lookup.get(file_name) or image_lookup.get(Path(file_name).name)
    if not source_image:
        raise FileNotFoundError(f"Image referenced by COCO JSON not found: {file_name}")

    target_name = unique_file_name(Path(file_name).name, written_names)
    target_image = image_dir / target_name
    target_label = label_dir / f"{Path(target_name).stem}.txt"
    shutil.copy2(source_image, target_image)
    target_label.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def unique_file_name(file_name: str, written_names: set[str]) -> str:
    candidate = file_name
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    index = 1
    while candidate in written_names:
        candidate = f"{stem}_{index}{suffix}"
        index += 1
    written_names.add(candidate)
    return candidate


def write_data_yaml(output: Path) -> None:
    data = {
        "path": output.as_posix(),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 1,
        "names": {0: "crack"},
    }
    with (output / "data.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=False)


def write_manifest(
    output: Path, summaries: list[SplitSummary], crack_names: set[str]
) -> None:
    manifest = {
        "source": {
            "repo_id": DEFAULT_REPO_ID,
            "license": "CC BY 4.0",
            "task": "object-detection",
            "selected_source_classes": sorted(crack_names),
        },
        "target": {
            "format": "YOLO",
            "classes": ["crack"],
        },
        "splits": [summary.__dict__ for summary in summaries],
    }
    with (output / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def print_summary(summaries: list[SplitSummary], output: Path) -> None:
    print("Stage A crack dataset prepared")
    print(f"Output: {output}")
    for summary in summaries:
        print(
            f"{summary.split}: images={summary.images}, positives={summary.positives}, "
            f"negatives={summary.negatives}, objects={summary.objects}, "
            f"skipped_objects={summary.skipped_objects}"
        )
    print(f"Data config: {output / 'data.yaml'}")


def main() -> int:
    args = parse_args()
    if args.download:
        download_dataset_files(args.source, args.repo_id, force=args.force)

    crack_names = set(args.crack_names or DEFAULT_CRACK_NAMES)
    summaries = prepare_dataset(
        args.source,
        args.output,
        crack_names=crack_names,
        negative_ratio=args.negative_ratio,
        include_negatives=not args.no_negatives,
        force=args.force,
    )
    print_summary(summaries, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
