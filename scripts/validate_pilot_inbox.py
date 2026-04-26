"""Validate the local pilot inbox before running Stage B training."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vision_analysis_pro.core.crack_yolo_dataset import (
    IMAGE_EXTENSIONS,
    validate_image_file,
    validate_label_file,
)

REQUIRED_MEDIA_FIELDS = (
    "asset_id",
    "device_id",
    "site_name",
    "capture_time",
    "source_type",
)
REQUIRED_REVIEW_FIELDS = ("reviewer", "review_rule_version")


@dataclass(frozen=True)
class PilotInboxSummary:
    """Validation summary for a local pilot inbox."""

    root: Path
    total_images: int
    labeled_images: int
    reviewed_positive_images: int
    reviewed_positive_boxes: int
    reviewed_negative_images: int
    pending_images: int
    metadata_records: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ready_for_he007(self) -> bool:
        """Return whether this inbox can enter the HE-007 real-pilot branch."""
        return not self.errors and self.reviewed_positive_boxes > 0

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable summary."""
        return {
            "created_at": datetime.now(UTC).isoformat(),
            "root": str(self.root),
            "total_images": self.total_images,
            "labeled_images": self.labeled_images,
            "reviewed_positive_images": self.reviewed_positive_images,
            "reviewed_positive_boxes": self.reviewed_positive_boxes,
            "reviewed_negative_images": self.reviewed_negative_images,
            "pending_images": self.pending_images,
            "metadata_records": self.metadata_records,
            "ready_for_he007": self.ready_for_he007,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate data/pilot_inbox before Stage B real-pilot training",
    )
    parser.add_argument(
        "--root",
        default="data/pilot_inbox",
        help="Pilot inbox root containing raw_images, reviewed_labels, and metadata",
    )
    parser.add_argument(
        "--raw-images-dir",
        default=None,
        help="Override raw image directory. Defaults to <root>/raw_images",
    )
    parser.add_argument(
        "--labels-dir",
        default=None,
        help="Override reviewed labels directory. Defaults to <root>/reviewed_labels",
    )
    parser.add_argument(
        "--metadata-dir",
        default=None,
        help="Override metadata directory. Defaults to <root>/metadata",
    )
    parser.add_argument(
        "--allow-no-positive",
        action="store_true",
        help="Allow structure-only validation when reviewed positive labels are absent",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of text summary",
    )
    return parser.parse_args()


def validate_pilot_inbox(
    root: Path,
    *,
    raw_images_dir: Path | None = None,
    labels_dir: Path | None = None,
    metadata_dir: Path | None = None,
    require_positive: bool = True,
) -> PilotInboxSummary:
    """Validate pilot media, labels, and handoff metadata."""
    raw_images_dir = raw_images_dir or root / "raw_images"
    labels_dir = labels_dir or root / "reviewed_labels"
    metadata_dir = metadata_dir or root / "metadata"

    errors: list[str] = []
    warnings: list[str] = []

    images = _collect_images(raw_images_dir, errors)
    metadata_by_stem = _load_metadata(metadata_dir, errors, warnings)
    label_files = _collect_label_files(labels_dir, errors)

    image_stems = {image.stem for image in images}
    label_stems = {label.stem for label in label_files}
    metadata_stems = set(metadata_by_stem)

    for image in images:
        try:
            validate_image_file(image)
        except ValueError as exc:
            errors.append(str(exc))

    for orphan_label in sorted(label_stems - image_stems):
        errors.append(f"reviewed label has no matching raw image: {orphan_label}.txt")

    for orphan_metadata in sorted(metadata_stems - image_stems):
        warnings.append(f"metadata has no matching raw image: {orphan_metadata}")

    labeled_images = 0
    reviewed_positive_images = 0
    reviewed_positive_boxes = 0
    reviewed_negative_images = 0
    pending_images = 0

    for image in images:
        metadata = metadata_by_stem.get(image.stem)
        if metadata is None:
            errors.append(f"missing metadata for raw image: {image.name}")
            metadata = {}
        _validate_required_fields(
            metadata,
            REQUIRED_MEDIA_FIELDS,
            errors,
            context=f"metadata for {image.name}",
        )

        label_path = labels_dir / f"{image.stem}.txt"
        if not label_path.exists():
            pending_images += 1
            continue

        labeled_images += 1
        _validate_required_fields(
            metadata,
            REQUIRED_REVIEW_FIELDS,
            errors,
            context=f"review metadata for {image.name}",
        )
        try:
            validate_label_file(label_path)
        except (ValueError, FileNotFoundError) as exc:
            errors.append(str(exc))
            continue

        box_count = _count_label_boxes(label_path)
        if box_count > 0:
            reviewed_positive_images += 1
            reviewed_positive_boxes += box_count
        else:
            reviewed_negative_images += 1

    if pending_images:
        warnings.append(
            f"{pending_images} raw image(s) do not have reviewed labels yet"
        )
    if require_positive and reviewed_positive_boxes == 0:
        errors.append(
            "no reviewed positive crack boxes found; do not enter HE-007 training"
        )

    return PilotInboxSummary(
        root=root,
        total_images=len(images),
        labeled_images=labeled_images,
        reviewed_positive_images=reviewed_positive_images,
        reviewed_positive_boxes=reviewed_positive_boxes,
        reviewed_negative_images=reviewed_negative_images,
        pending_images=pending_images,
        metadata_records=len(metadata_by_stem),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _collect_images(raw_images_dir: Path, errors: list[str]) -> list[Path]:
    if not raw_images_dir.exists():
        errors.append(f"missing raw images directory: {raw_images_dir}")
        return []
    if not raw_images_dir.is_dir():
        errors.append(f"raw images path is not a directory: {raw_images_dir}")
        return []
    images = sorted(
        path
        for path in raw_images_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        errors.append(f"no supported raw images found in {raw_images_dir}")
    return images


def _collect_label_files(labels_dir: Path, errors: list[str]) -> list[Path]:
    if not labels_dir.exists():
        errors.append(f"missing reviewed labels directory: {labels_dir}")
        return []
    if not labels_dir.is_dir():
        errors.append(f"reviewed labels path is not a directory: {labels_dir}")
        return []
    return sorted(path for path in labels_dir.rglob("*.txt") if path.is_file())


def _load_metadata(
    metadata_dir: Path,
    errors: list[str],
    warnings: list[str],
) -> dict[str, dict[str, Any]]:
    if not metadata_dir.exists():
        errors.append(f"missing metadata directory: {metadata_dir}")
        return {}
    if not metadata_dir.is_dir():
        errors.append(f"metadata path is not a directory: {metadata_dir}")
        return {}

    records: dict[str, dict[str, Any]] = {}
    for path in sorted(metadata_dir.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path} is not valid JSON: {exc}")
            continue
        _merge_metadata_records(path, data, records, errors, warnings)
    return records


def _merge_metadata_records(
    path: Path,
    data: object,
    records: dict[str, dict[str, Any]],
    errors: list[str],
    warnings: list[str],
) -> None:
    if isinstance(data, list):
        for item in data:
            _add_metadata_item(path, item, records, errors, warnings)
        return
    if not isinstance(data, dict):
        errors.append(f"{path} must contain an object, list, or items list")
        return

    if isinstance(data.get("items"), list):
        for item in data["items"]:
            _add_metadata_item(path, item, records, errors, warnings)
        return

    if _looks_like_record(data):
        stem = str(data.get("image_stem") or Path(str(data.get("image", path.stem))).stem)
        _store_metadata_record(path, stem, data, records, warnings)
        return

    for stem, value in data.items():
        if not isinstance(value, dict):
            errors.append(f"{path}:{stem} metadata value must be an object")
            continue
        _store_metadata_record(path, str(stem), value, records, warnings)


def _add_metadata_item(
    path: Path,
    item: object,
    records: dict[str, dict[str, Any]],
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(item, dict):
        errors.append(f"{path} items must be objects")
        return
    stem_value = item.get("image_stem") or item.get("image") or item.get("filename")
    if not stem_value:
        errors.append(f"{path} metadata item missing image_stem or image")
        return
    _store_metadata_record(path, Path(str(stem_value)).stem, item, records, warnings)


def _store_metadata_record(
    path: Path,
    stem: str,
    record: dict[str, Any],
    records: dict[str, dict[str, Any]],
    warnings: list[str],
) -> None:
    if stem in records:
        warnings.append(f"duplicate metadata for {stem}; using record from {path}")
    records[stem] = record


def _looks_like_record(data: dict[str, Any]) -> bool:
    known_fields = set(REQUIRED_MEDIA_FIELDS).union(REQUIRED_REVIEW_FIELDS)
    return bool(known_fields.intersection(data) or {"image", "image_stem"} & set(data))


def _validate_required_fields(
    record: dict[str, Any],
    fields: tuple[str, ...],
    errors: list[str],
    *,
    context: str,
) -> None:
    missing = [field for field in fields if not str(record.get(field, "")).strip()]
    if missing:
        errors.append(f"{context} missing required field(s): {', '.join(missing)}")


def _count_label_boxes(label_path: Path) -> int:
    return sum(
        1 for line in label_path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def _print_text_summary(summary: PilotInboxSummary) -> None:
    print(f"pilot_inbox={summary.root}")
    print(f"total_images={summary.total_images}")
    print(f"labeled_images={summary.labeled_images}")
    print(f"pending_images={summary.pending_images}")
    print(f"reviewed_positive_images={summary.reviewed_positive_images}")
    print(f"reviewed_positive_boxes={summary.reviewed_positive_boxes}")
    print(f"reviewed_negative_images={summary.reviewed_negative_images}")
    print(f"metadata_records={summary.metadata_records}")
    print(f"ready_for_he007={str(summary.ready_for_he007).lower()}")
    for warning in summary.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for error in summary.errors:
        print(f"error: {error}", file=sys.stderr)


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    summary = validate_pilot_inbox(
        root,
        raw_images_dir=Path(args.raw_images_dir) if args.raw_images_dir else None,
        labels_dir=Path(args.labels_dir) if args.labels_dir else None,
        metadata_dir=Path(args.metadata_dir) if args.metadata_dir else None,
        require_positive=not args.allow_no_positive,
    )

    if args.json:
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_text_summary(summary)

    if summary.errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
