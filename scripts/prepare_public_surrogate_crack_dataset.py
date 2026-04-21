"""Prepare a crack-only public surrogate dataset from SDNET2018 and RDD2022."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import cv2

from vision_analysis_pro.core.crack_yolo_dataset import (
    IMAGE_EXTENSIONS,
    SPLITS,
    validate_label_lines,
    validate_prepared_dataset,
    write_crack_data_yaml,
)

DEFAULT_RDD_CRACK_CLASSES = ("D00", "D10", "D20")
SDNET_NEGATIVE_MARKERS = {"noncrack", "non-crack", "uncracked", "negative"}
SDNET_POSITIVE_MARKERS = {"crack", "positive"}


@dataclass(frozen=True)
class PublicCandidate:
    """One public-source image and its crack-only YOLO labels."""

    image_path: Path
    label_lines: list[str]
    source_dataset: str
    source_kind: str
    annotation_status: str
    source_annotation: Path | None = None


@dataclass(frozen=True)
class PreparedPublicDataset:
    """Prepared public surrogate dataset summary."""

    output: Path
    total_images: int
    labeled_images: int
    empty_label_images: int
    split_counts: dict[str, int]
    source_summary: dict[str, dict[str, int]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a crack-only public surrogate dataset from SDNET2018 and RDD2022",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/stage_b_public_surrogate_crack"),
        help="Output dataset directory",
    )
    parser.add_argument(
        "--sdnet2018-source",
        type=Path,
        default=None,
        help="Extracted SDNET2018 root directory",
    )
    parser.add_argument(
        "--sdnet2018-crack-auto-label-model",
        type=Path,
        default=None,
        help="Optional ONNX model path used to auto-label SDNET2018 Crack images",
    )
    parser.add_argument(
        "--rdd2022-source",
        type=Path,
        default=None,
        help="Extracted RDD2022 root directory",
    )
    parser.add_argument(
        "--rdd-crack-class",
        action="append",
        dest="rdd_crack_classes",
        default=None,
        help="RDD2022 class name to treat as crack. Repeatable; defaults to D00/D10/D20.",
    )
    parser.add_argument(
        "--skip-rdd-non-crack-negatives",
        action="store_true",
        help="Ignore RDD2022 images that have only non-crack damage classes",
    )
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--conf",
        type=float,
        default=0.30,
        help="Confidence threshold for optional SDNET2018 ONNX auto-labeling",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.45,
        help="NMS IoU threshold for optional SDNET2018 ONNX auto-labeling",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate an existing output dataset",
    )
    return parser.parse_args()


def prepare_dataset(
    output: Path,
    *,
    sdnet2018_source: Path | None = None,
    sdnet2018_crack_auto_label_model: Path | None = None,
    rdd2022_source: Path | None = None,
    rdd_crack_classes: set[str] | None = None,
    include_rdd_non_crack_negatives: bool = True,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    conf: float = 0.30,
    iou: float = 0.45,
) -> PreparedPublicDataset:
    """Build a crack-only public surrogate dataset from supported sources."""
    _validate_ratios(train_ratio, val_ratio, test_ratio)
    output.mkdir(parents=True, exist_ok=True)
    _reset_generated_dirs(output)
    source_summary: dict[str, dict[str, int]] = {}
    candidates: list[PublicCandidate] = []

    if sdnet2018_source is not None:
        sdnet_candidates, sdnet_summary = collect_sdnet2018_candidates(
            sdnet2018_source,
            crack_auto_label_model=sdnet2018_crack_auto_label_model,
            conf=conf,
            iou=iou,
        )
        candidates.extend(sdnet_candidates)
        source_summary["sdnet2018"] = sdnet_summary

    if rdd2022_source is not None:
        rdd_candidates, rdd_summary = collect_rdd2022_candidates(
            rdd2022_source,
            crack_classes={
                item.upper()
                for item in (rdd_crack_classes or set(DEFAULT_RDD_CRACK_CLASSES))
            },
            include_non_crack_negatives=include_rdd_non_crack_negatives,
        )
        candidates.extend(rdd_candidates)
        source_summary["rdd2022"] = rdd_summary

    if not candidates:
        raise ValueError("no public surrogate candidates were found")

    _prepare_output_dirs(output)
    split_map = split_candidates(
        candidates,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        seed=seed,
    )

    labeled_images = 0
    empty_label_images = 0
    manifest_items: list[dict[str, object]] = []
    for split, split_candidates_ in split_map.items():
        for index, candidate in enumerate(split_candidates_):
            image_name = _stable_image_name(candidate, index)
            image_target = output / "images" / split / image_name
            label_target = output / "labels" / split / f"{Path(image_name).stem}.txt"
            shutil.copy2(candidate.image_path, image_target)
            validate_label_lines(
                candidate.label_lines,
                source_name=str(candidate.source_annotation or candidate.image_path),
            )
            label_target.write_text("\n".join(candidate.label_lines), encoding="utf-8")
            if candidate.label_lines:
                labeled_images += 1
            else:
                empty_label_images += 1
            manifest_items.append(
                {
                    "split": split,
                    "image": str(image_target),
                    "label": str(label_target),
                    "source": str(candidate.image_path),
                    "source_dataset": candidate.source_dataset,
                    "source_kind": candidate.source_kind,
                    "source_annotation": (
                        str(candidate.source_annotation)
                        if candidate.source_annotation is not None
                        else None
                    ),
                    "annotation_status": candidate.annotation_status,
                }
            )

    write_crack_data_yaml(output)
    split_counts = {split: len(items) for split, items in split_map.items()}
    write_manifest(
        output,
        split_counts=split_counts,
        labeled_images=labeled_images,
        empty_label_images=empty_label_images,
        source_summary=source_summary,
        items=manifest_items,
        seed=seed,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
    )
    validate_prepared_dataset(output)

    return PreparedPublicDataset(
        output=output,
        total_images=sum(split_counts.values()),
        labeled_images=labeled_images,
        empty_label_images=empty_label_images,
        split_counts=split_counts,
        source_summary=source_summary,
    )


def collect_sdnet2018_candidates(
    source: Path,
    *,
    crack_auto_label_model: Path | None,
    conf: float,
    iou: float,
) -> tuple[list[PublicCandidate], dict[str, int]]:
    """Collect SDNET2018 images as reviewed negatives and optional proxy positives."""
    if not source.exists():
        raise FileNotFoundError(f"SDNET2018 source does not exist: {source}")

    auto_label_fn = None
    if crack_auto_label_model is not None:
        auto_label_fn = _build_sdnet_auto_labeler(crack_auto_label_model, conf=conf, iou=iou)

    candidates: list[PublicCandidate] = []
    summary = {
        "reviewed_negative_images": 0,
        "proxy_labeled_crack_images": 0,
        "skipped_crack_images_without_labels": 0,
    }
    for image_path in _iter_media_images(source):
        lower_parts = {part.lower() for part in image_path.parts}
        if lower_parts & SDNET_NEGATIVE_MARKERS:
            candidates.append(
                PublicCandidate(
                    image_path=image_path,
                    label_lines=[],
                    source_dataset="sdnet2018",
                    source_kind="classification_negative",
                    annotation_status="sdnet2018_reviewed_negative",
                )
            )
            summary["reviewed_negative_images"] += 1
            continue

        if lower_parts & SDNET_POSITIVE_MARKERS:
            if auto_label_fn is None:
                summary["skipped_crack_images_without_labels"] += 1
                continue
            label_lines = auto_label_fn(image_path)
            if not label_lines:
                summary["skipped_crack_images_without_labels"] += 1
                continue
            candidates.append(
                PublicCandidate(
                    image_path=image_path,
                    label_lines=label_lines,
                    source_dataset="sdnet2018",
                    source_kind="classification_proxy_positive",
                    annotation_status="sdnet2018_proxy_auto_labeled",
                    source_annotation=crack_auto_label_model,
                )
            )
            summary["proxy_labeled_crack_images"] += 1

    return candidates, summary


def collect_rdd2022_candidates(
    source: Path,
    *,
    crack_classes: set[str],
    include_non_crack_negatives: bool,
) -> tuple[list[PublicCandidate], dict[str, int]]:
    """Collect crack-only candidates from RDD2022 Pascal VOC XML annotations."""
    if not source.exists():
        raise FileNotFoundError(f"RDD2022 source does not exist: {source}")

    xml_index = _index_pascal_voc_annotations(source)
    candidates: list[PublicCandidate] = []
    summary = {
        "labeled_crack_images": 0,
        "reviewed_negative_images": 0,
        "skipped_images_without_annotation": 0,
    }

    for image_path in _iter_media_images(source):
        annotation_path = _find_pascal_voc_annotation(image_path, xml_index)
        if annotation_path is None:
            summary["skipped_images_without_annotation"] += 1
            continue
        label_lines = parse_rdd2022_xml(annotation_path, crack_classes=crack_classes)
        if label_lines:
            candidates.append(
                PublicCandidate(
                    image_path=image_path,
                    label_lines=label_lines,
                    source_dataset="rdd2022",
                    source_kind="pascal_voc",
                    annotation_status="rdd2022_reviewed_label",
                    source_annotation=annotation_path,
                )
            )
            summary["labeled_crack_images"] += 1
            continue
        if include_non_crack_negatives:
            candidates.append(
                PublicCandidate(
                    image_path=image_path,
                    label_lines=[],
                    source_dataset="rdd2022",
                    source_kind="pascal_voc_non_crack",
                    annotation_status="rdd2022_reviewed_negative",
                    source_annotation=annotation_path,
                )
            )
            summary["reviewed_negative_images"] += 1

    return candidates, summary


def parse_rdd2022_xml(annotation_path: Path, *, crack_classes: set[str]) -> list[str]:
    """Convert one Pascal VOC annotation file to crack-only YOLO labels."""
    root = ET.parse(annotation_path).getroot()
    size = root.find("size")
    if size is None:
        raise ValueError(f"{annotation_path} missing <size> node")
    width = int(_xml_text(size, "width"))
    height = int(_xml_text(size, "height"))
    if width <= 0 or height <= 0:
        raise ValueError(f"{annotation_path} has invalid image size")

    lines: list[str] = []
    for obj in root.findall("object"):
        label = _xml_text(obj, "name").upper()
        if label not in crack_classes:
            continue
        bbox = obj.find("bndbox")
        if bbox is None:
            raise ValueError(f"{annotation_path} missing <bndbox> for {label}")
        xmin = float(_xml_text(bbox, "xmin"))
        ymin = float(_xml_text(bbox, "ymin"))
        xmax = float(_xml_text(bbox, "xmax"))
        ymax = float(_xml_text(bbox, "ymax"))
        yolo_bbox = bbox_to_yolo(xmin, ymin, xmax, ymax, width, height)
        lines.append(
            f"0 {yolo_bbox[0]:.6f} {yolo_bbox[1]:.6f} {yolo_bbox[2]:.6f} {yolo_bbox[3]:.6f}"
        )
    return lines


def bbox_to_yolo(
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float]:
    """Convert one Pascal VOC bbox to normalized YOLO format."""
    width = max(0.0, xmax - xmin)
    height = max(0.0, ymax - ymin)
    center_x = xmin + width / 2.0
    center_y = ymin + height / 2.0
    return (
        max(0.0, min(1.0, center_x / image_width)),
        max(0.0, min(1.0, center_y / image_height)),
        max(0.0, min(1.0, width / image_width)),
        max(0.0, min(1.0, height / image_height)),
    )


def split_candidates(
    candidates: list[PublicCandidate],
    *,
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> dict[str, list[PublicCandidate]]:
    """Split candidates deterministically into train/val/test."""
    shuffled = candidates.copy()
    random.Random(seed).shuffle(shuffled)
    total = len(shuffled)
    train_count = int(total * train_ratio)
    val_count = int(total * val_ratio)

    if total > 0 and train_count == 0:
        train_count = 1
    if total >= 3 and val_count == 0:
        val_count = 1
    if train_count + val_count > total:
        val_count = max(0, total - train_count)

    return {
        "train": shuffled[:train_count],
        "val": shuffled[train_count : train_count + val_count],
        "test": shuffled[train_count + val_count :],
    }


def write_manifest(
    output: Path,
    *,
    split_counts: dict[str, int],
    labeled_images: int,
    empty_label_images: int,
    source_summary: dict[str, dict[str, int]],
    items: list[dict[str, object]],
    seed: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> None:
    """Write dataset manifest for public surrogate auditability."""
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "target": {
            "stage": "B",
            "dataset": "stage_b_public_surrogate_crack",
            "mode": "public_surrogate",
            "classes": ["crack"],
        },
        "settings": {
            "seed": seed,
            "split_ratios": {
                "train": train_ratio,
                "val": val_ratio,
                "test": test_ratio,
            },
        },
        "split_counts": split_counts,
        "annotation_status": {
            "labeled_images": labeled_images,
            "reviewed_images": labeled_images + empty_label_images,
            "reviewed_negative_empty_label_images": empty_label_images,
        },
        "source_summary": source_summary,
        "items": items,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_sdnet_auto_labeler(
    model_path: Path, *, conf: float, iou: float
) -> Callable[[Path], list[str]]:
    from vision_analysis_pro.core.inference.onnx_engine import ONNXInferenceEngine

    engine = ONNXInferenceEngine(model_path=str(model_path))

    def auto_label(image_path: Path) -> list[str]:
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"{image_path} is not a readable image")
        image_height, image_width = image.shape[:2]
        detections = engine.predict(image, conf=conf, iou=iou)
        lines: list[str] = []
        for detection in detections:
            xmin, ymin, xmax, ymax = detection["bbox"]
            yolo_bbox = bbox_to_yolo(xmin, ymin, xmax, ymax, image_width, image_height)
            lines.append(
                f"0 {yolo_bbox[0]:.6f} {yolo_bbox[1]:.6f} {yolo_bbox[2]:.6f} {yolo_bbox[3]:.6f}"
            )
        return lines

    return auto_label


def _index_pascal_voc_annotations(source: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for annotation_path in sorted(source.rglob("*.xml")):
        index.setdefault(annotation_path.stem, []).append(annotation_path)
    return index


def _find_pascal_voc_annotation(
    image_path: Path, annotation_index: dict[str, list[Path]]
) -> Path | None:
    direct_candidate = image_path.with_suffix(".xml")
    if direct_candidate.exists():
        return direct_candidate
    matches = annotation_index.get(image_path.stem, [])
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    image_parts = image_path.parts
    return max(
        matches,
        key=lambda candidate: _shared_suffix_length(image_parts, candidate.parts),
    )


def _shared_suffix_length(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    count = 0
    for left_part, right_part in zip(reversed(left), reversed(right), strict=False):
        if left_part != right_part:
            break
        count += 1
    return count


def _iter_media_images(path: Path) -> list[Path]:
    return sorted(
        item
        for item in path.rglob("*")
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def _prepare_output_dirs(output: Path) -> None:
    for split in SPLITS:
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)


def _reset_generated_dirs(output: Path) -> None:
    for child in ("images", "labels"):
        path = output / child
        if path.exists():
            shutil.rmtree(path)


def _stable_image_name(candidate: PublicCandidate, index: int) -> str:
    source_stem = _safe_stem(candidate.image_path)
    prefix = f"{candidate.source_dataset}_{candidate.source_kind}"
    return f"{prefix}_{source_stem}_{index:05d}{candidate.image_path.suffix.lower()}"


def _safe_stem(path: Path) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in path.stem)


def _validate_ratios(train_ratio: float, val_ratio: float, test_ratio: float) -> None:
    if train_ratio < 0 or val_ratio < 0 or test_ratio < 0:
        raise ValueError("split ratios must be >= 0")
    total = train_ratio + val_ratio + test_ratio
    if not 0.999 <= total <= 1.001:
        raise ValueError("train/val/test ratios must sum to 1.0")


def _xml_text(node: ET.Element, child_name: str) -> str:
    child = node.find(child_name)
    if child is None or child.text is None:
        raise ValueError(f"missing <{child_name}> in Pascal VOC annotation")
    return child.text.strip()


def main() -> None:
    args = parse_args()
    if args.validate_only:
        validate_prepared_dataset(args.output)
        print(f"validated public surrogate dataset: {args.output}")
        return

    prepared = prepare_dataset(
        args.output,
        sdnet2018_source=args.sdnet2018_source,
        sdnet2018_crack_auto_label_model=args.sdnet2018_crack_auto_label_model,
        rdd2022_source=args.rdd2022_source,
        rdd_crack_classes=set(args.rdd_crack_classes or DEFAULT_RDD_CRACK_CLASSES),
        include_rdd_non_crack_negatives=not args.skip_rdd_non_crack_negatives,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
        conf=args.conf,
        iou=args.iou,
    )

    print(f"prepared public surrogate dataset: {prepared.output}")
    print(f"total_images={prepared.total_images}")
    print(f"labeled_images={prepared.labeled_images}")
    print(f"reviewed_negative_empty_label_images={prepared.empty_label_images}")
    print(f"split_counts={prepared.split_counts}")
    print(f"source_summary={prepared.source_summary}")


if __name__ == "__main__":
    main()
