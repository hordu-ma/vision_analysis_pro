"""Prepare a Stage B crack-only pilot YOLO dataset from local media."""

from __future__ import annotations

import argparse
import json
import random
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import cv2

from vision_analysis_pro.core.preprocessing.keyframes import (
    KeyframeOptions,
    extract_keyframes,
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class Candidate:
    """One source image ready to be assigned to a YOLO split."""

    image_path: Path
    label_path: Path | None
    source_path: Path
    source_kind: str


@dataclass(frozen=True)
class PreparedDataset:
    """Prepared Stage B dataset summary."""

    output: Path
    total_images: int
    labeled_images: int
    empty_label_images: int
    reviewed_images: int
    reviewed_empty_label_images: int
    split_counts: dict[str, int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a Stage B crack-only pilot YOLO dataset from images/videos",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Input image/video files or directories containing pilot media",
    )
    parser.add_argument(
        "--output",
        default="data/stage_b_pilot_crack",
        help="Output dataset directory",
    )
    parser.add_argument(
        "--labels-dir",
        default=None,
        help="Optional directory containing YOLO .txt labels matched by image stem",
    )
    parser.add_argument(
        "--allow-unlabeled",
        action="store_true",
        help="Create empty label files for images that are still pending annotation",
    )
    parser.add_argument(
        "--mark-reviewed",
        action="store_true",
        help=(
            "Mark supplied labels, or empty labels created with --allow-unlabeled, "
            "as human reviewed in manifest.json"
        ),
    )
    parser.add_argument(
        "--extract-videos",
        action="store_true",
        help="Extract keyframes from video inputs before dataset split",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=1.0,
        help="Video keyframe fixed extraction interval",
    )
    parser.add_argument(
        "--min-scene-delta",
        type=float,
        default=20.0,
        help="Video keyframe scene-change threshold",
    )
    parser.add_argument(
        "--blur-threshold",
        type=float,
        default=10.0,
        help="Video keyframe blur threshold",
    )
    parser.add_argument(
        "--max-frames-per-video",
        type=int,
        default=None,
        help="Optional maximum keyframes per video",
    )
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate an existing output dataset",
    )
    return parser.parse_args()


def prepare_dataset(
    inputs: list[Path],
    output: Path,
    *,
    labels_dir: Path | None = None,
    allow_unlabeled: bool = False,
    mark_reviewed: bool = False,
    extract_videos: bool = False,
    interval_seconds: float = 1.0,
    min_scene_delta: float = 20.0,
    blur_threshold: float = 10.0,
    max_frames_per_video: int | None = None,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> PreparedDataset:
    """Prepare a crack-only YOLO dataset from pilot media."""
    _validate_ratios(train_ratio, val_ratio, test_ratio)
    output.mkdir(parents=True, exist_ok=True)
    raw_keyframes_dir = output / "raw_keyframes"
    _reset_generated_dirs(output)
    candidates = collect_candidates(
        inputs,
        labels_dir=labels_dir,
        output_keyframes_dir=raw_keyframes_dir,
        extract_videos=extract_videos,
        interval_seconds=interval_seconds,
        min_scene_delta=min_scene_delta,
        blur_threshold=blur_threshold,
        max_frames_per_video=max_frames_per_video,
    )
    if not candidates:
        raise ValueError("no supported images were found in Stage B inputs")

    _prepare_output_dirs(output)
    split_map = split_candidates(
        candidates,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        seed=seed,
    )

    labeled_images = 0
    empty_label_images = 0
    reviewed_images = 0
    reviewed_empty_label_images = 0
    copied_sources: list[dict[str, object]] = []

    for split, split_candidates_ in split_map.items():
        for index, candidate in enumerate(split_candidates_):
            image_name = _stable_image_name(candidate, index)
            image_target = output / "images" / split / image_name
            label_target = output / "labels" / split / f"{Path(image_name).stem}.txt"
            shutil.copy2(candidate.image_path, image_target)

            if candidate.label_path is not None:
                validate_label_file(candidate.label_path)
                shutil.copy2(candidate.label_path, label_target)
                labeled_images += 1
                if mark_reviewed:
                    reviewed_images += 1
                    annotation_status = "reviewed_label"
                else:
                    annotation_status = "labeled"
            elif allow_unlabeled:
                label_target.write_text("", encoding="utf-8")
                empty_label_images += 1
                if mark_reviewed:
                    reviewed_images += 1
                    reviewed_empty_label_images += 1
                    annotation_status = "reviewed_negative_empty_label"
                else:
                    annotation_status = "pending_annotation_empty_label"
            else:
                raise FileNotFoundError(
                    "missing YOLO label for "
                    f"{candidate.image_path}; pass --labels-dir or --allow-unlabeled"
                )

            copied_sources.append(
                {
                    "split": split,
                    "image": str(image_target),
                    "label": str(label_target),
                    "source": str(candidate.source_path),
                    "source_kind": candidate.source_kind,
                    "annotation_status": annotation_status,
                }
            )

    write_data_yaml(output)
    split_counts = {split: len(items) for split, items in split_map.items()}
    write_manifest(
        output,
        inputs=inputs,
        labels_dir=labels_dir,
        allow_unlabeled=allow_unlabeled,
        mark_reviewed=mark_reviewed,
        extract_videos=extract_videos,
        interval_seconds=interval_seconds,
        min_scene_delta=min_scene_delta,
        blur_threshold=blur_threshold,
        max_frames_per_video=max_frames_per_video,
        seed=seed,
        split_counts=split_counts,
        labeled_images=labeled_images,
        empty_label_images=empty_label_images,
        reviewed_images=reviewed_images,
        reviewed_empty_label_images=reviewed_empty_label_images,
        copied_sources=copied_sources,
    )
    validate_prepared_dataset(output)

    return PreparedDataset(
        output=output,
        total_images=sum(split_counts.values()),
        labeled_images=labeled_images,
        empty_label_images=empty_label_images,
        reviewed_images=reviewed_images,
        reviewed_empty_label_images=reviewed_empty_label_images,
        split_counts=split_counts,
    )


def collect_candidates(
    inputs: list[Path],
    *,
    labels_dir: Path | None,
    output_keyframes_dir: Path,
    extract_videos: bool,
    interval_seconds: float,
    min_scene_delta: float,
    blur_threshold: float,
    max_frames_per_video: int | None,
) -> list[Candidate]:
    """Collect image candidates from files, directories, and optional videos."""
    candidates: list[Candidate] = []
    for input_path in inputs:
        if not input_path.exists():
            raise FileNotFoundError(f"Stage B input does not exist: {input_path}")

        for media_path in _iter_media(input_path):
            suffix = media_path.suffix.lower()
            if suffix in IMAGE_EXTENSIONS:
                candidates.append(
                    Candidate(
                        image_path=media_path,
                        label_path=_find_label(media_path, labels_dir),
                        source_path=media_path,
                        source_kind="image",
                    )
                )
            elif suffix in VIDEO_EXTENSIONS:
                if not extract_videos:
                    raise ValueError(
                        f"video input requires --extract-videos: {media_path}"
                    )
                candidates.extend(
                    _extract_video_candidates(
                        media_path,
                        output_keyframes_dir=output_keyframes_dir,
                        interval_seconds=interval_seconds,
                        min_scene_delta=min_scene_delta,
                        blur_threshold=blur_threshold,
                        max_frames_per_video=max_frames_per_video,
                    )
                )
    return sorted(candidates, key=lambda candidate: str(candidate.image_path))


def split_candidates(
    candidates: list[Candidate],
    *,
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> dict[str, list[Candidate]]:
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


def validate_prepared_dataset(output: Path) -> None:
    """Validate image/label pairing and YOLO label format."""
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
    """Validate that a dataset image is readable by OpenCV."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"{image_path} is not a readable image")


def validate_label_file(label_path: Path) -> None:
    """Validate one crack-only YOLO label file."""
    lines = label_path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != 5:
            raise ValueError(f"{label_path}:{line_number} must contain 5 fields")
        class_id = int(parts[0])
        if class_id != 0:
            raise ValueError(f"{label_path}:{line_number} only class id 0 is allowed")
        center_x, center_y, width, height = map(float, parts[1:])
        if not (
            0 <= center_x <= 1
            and 0 <= center_y <= 1
            and 0 < width <= 1
            and 0 < height <= 1
        ):
            raise ValueError(f"{label_path}:{line_number} bbox values out of range")


def write_data_yaml(output: Path) -> None:
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


def write_manifest(
    output: Path,
    *,
    inputs: list[Path],
    labels_dir: Path | None,
    allow_unlabeled: bool,
    mark_reviewed: bool,
    extract_videos: bool,
    interval_seconds: float,
    min_scene_delta: float,
    blur_threshold: float,
    max_frames_per_video: int | None,
    seed: int,
    split_counts: dict[str, int],
    labeled_images: int,
    empty_label_images: int,
    reviewed_images: int,
    reviewed_empty_label_images: int,
    copied_sources: list[dict[str, object]],
) -> None:
    """Write dataset manifest for auditability."""
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "target": {
            "stage": "B",
            "dataset": "stage_b_pilot_crack",
            "classes": ["crack"],
        },
        "inputs": [str(path) for path in inputs],
        "labels_dir": str(labels_dir) if labels_dir else None,
        "settings": {
            "allow_unlabeled": allow_unlabeled,
            "mark_reviewed": mark_reviewed,
            "seed": seed,
            "extract_videos": extract_videos,
            "keyframes": {
                "interval_seconds": interval_seconds,
                "min_scene_delta": min_scene_delta,
                "blur_threshold": blur_threshold,
                "max_frames_per_video": max_frames_per_video,
            },
        },
        "split_counts": split_counts,
        "annotation_status": {
            "labeled_images": labeled_images,
            "pending_annotation_empty_label_images": (
                empty_label_images - reviewed_empty_label_images
            ),
            "reviewed_images": reviewed_images,
            "reviewed_negative_empty_label_images": reviewed_empty_label_images,
        },
        "items": copied_sources,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _prepare_output_dirs(output: Path) -> None:
    for split in SPLITS:
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)


def _reset_generated_dirs(output: Path) -> None:
    for child in ("images", "labels", "raw_keyframes"):
        path = output / child
        if path.exists():
            shutil.rmtree(path)


def _iter_media(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(
        item
        for item in path.rglob("*")
        if item.is_file()
        and item.suffix.lower() in IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)
    )


def _iter_images(path: Path) -> list[Path]:
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def _find_label(image_path: Path, labels_dir: Path | None) -> Path | None:
    candidates = []
    if labels_dir is not None:
        candidates.append(labels_dir / f"{image_path.stem}.txt")
    candidates.append(image_path.with_suffix(".txt"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _extract_video_candidates(
    video_path: Path,
    *,
    output_keyframes_dir: Path,
    interval_seconds: float,
    min_scene_delta: float,
    blur_threshold: float,
    max_frames_per_video: int | None,
) -> list[Candidate]:
    video_output_dir = output_keyframes_dir / _safe_stem(video_path)
    keyframes = extract_keyframes(
        video_path,
        KeyframeOptions(
            interval_seconds=interval_seconds,
            min_scene_delta=min_scene_delta,
            blur_threshold=blur_threshold,
            max_frames=max_frames_per_video,
            output_dir=video_output_dir,
        ),
    )
    return [
        Candidate(
            image_path=keyframe.output_path,
            label_path=None,
            source_path=video_path,
            source_kind="video_keyframe",
        )
        for keyframe in keyframes
        if keyframe.output_path is not None
    ]


def _stable_image_name(candidate: Candidate, index: int) -> str:
    source_stem = _safe_stem(candidate.source_path)
    return f"{source_stem}_{index:05d}{candidate.image_path.suffix.lower()}"


def _safe_stem(path: Path) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in path.stem)


def _validate_ratios(train_ratio: float, val_ratio: float, test_ratio: float) -> None:
    if train_ratio < 0 or val_ratio < 0 or test_ratio < 0:
        raise ValueError("split ratios must be >= 0")
    total = train_ratio + val_ratio + test_ratio
    if not 0.999 <= total <= 1.001:
        raise ValueError("train/val/test ratios must sum to 1.0")


def main() -> None:
    args = parse_args()
    if args.validate_only:
        validate_prepared_dataset(Path(args.output))
        print(f"validated Stage B dataset: {args.output}")
        return

    if not args.inputs:
        raise SystemExit("at least one input is required unless --validate-only is set")

    prepared = prepare_dataset(
        [Path(item) for item in args.inputs],
        Path(args.output),
        labels_dir=Path(args.labels_dir) if args.labels_dir else None,
        allow_unlabeled=args.allow_unlabeled,
        mark_reviewed=args.mark_reviewed,
        extract_videos=args.extract_videos,
        interval_seconds=args.interval_seconds,
        min_scene_delta=args.min_scene_delta,
        blur_threshold=args.blur_threshold,
        max_frames_per_video=args.max_frames_per_video,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )

    print(f"prepared Stage B dataset: {prepared.output}")
    print(f"total_images={prepared.total_images}")
    print(f"labeled_images={prepared.labeled_images}")
    print(
        "pending_annotation_empty_label_images="
        f"{prepared.empty_label_images - prepared.reviewed_empty_label_images}"
    )
    print(f"reviewed_images={prepared.reviewed_images}")
    print(
        f"reviewed_negative_empty_label_images={prepared.reviewed_empty_label_images}"
    )
    print(f"split_counts={prepared.split_counts}")


if __name__ == "__main__":
    main()
