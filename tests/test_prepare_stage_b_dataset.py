"""Tests for preparing the Stage B pilot YOLO dataset."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml


def load_prepare_module():
    script_path = Path("scripts/prepare_stage_b_pilot_dataset.py")
    spec = importlib.util.spec_from_file_location(
        "prepare_stage_b_pilot_dataset",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_image(path: Path) -> None:
    image = np.full((64, 64, 3), 128, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def write_video(path: Path, *, fps: float = 2.0) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (64, 64))
    assert writer.isOpened()
    try:
        for value in [0, 0, 255, 255, 128]:
            frame = np.full((64, 64, 3), value, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def test_prepare_stage_b_dataset_copies_images_labels_and_manifest(
    tmp_path: Path,
) -> None:
    module = load_prepare_module()
    source = tmp_path / "pilot"
    labels = tmp_path / "labels"
    output = tmp_path / "stage_b"
    source.mkdir()
    labels.mkdir()

    for index in range(4):
        write_image(source / f"frame_{index}.jpg")
        (labels / f"frame_{index}.txt").write_text(
            "0 0.500000 0.500000 0.250000 0.250000\n",
            encoding="utf-8",
        )

    summary = module.prepare_dataset(
        [source],
        output,
        labels_dir=labels,
        train_ratio=0.5,
        val_ratio=0.25,
        test_ratio=0.25,
    )

    assert summary.total_images == 4
    assert summary.labeled_images == 4
    assert (output / "data.yaml").exists()
    assert (output / "manifest.json").exists()

    with (output / "data.yaml").open("r", encoding="utf-8") as f:
        data_config = yaml.safe_load(f)
    assert data_config["nc"] == 1
    assert data_config["names"] == {0: "crack"}

    with (output / "manifest.json").open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["split_counts"] == {"train": 2, "val": 1, "test": 1}
    assert manifest["annotation_status"]["labeled_images"] == 4


def test_prepare_stage_b_dataset_requires_labels_unless_allowed(
    tmp_path: Path,
) -> None:
    module = load_prepare_module()
    source = tmp_path / "pilot"
    source.mkdir()
    write_image(source / "frame_0.jpg")

    with pytest.raises(FileNotFoundError, match="missing YOLO label"):
        module.prepare_dataset([source], tmp_path / "stage_b")

    summary = module.prepare_dataset(
        [source],
        tmp_path / "stage_b_unlabeled",
        allow_unlabeled=True,
    )

    assert summary.empty_label_images == 1
    label_files = list((tmp_path / "stage_b_unlabeled").glob("labels/*/*.txt"))
    assert len(label_files) == 1
    assert label_files[0].read_text(encoding="utf-8") == ""


def test_prepare_stage_b_dataset_resets_generated_files(tmp_path: Path) -> None:
    module = load_prepare_module()
    source = tmp_path / "pilot"
    output = tmp_path / "stage_b"
    source.mkdir()
    write_image(source / "frame_0.jpg")
    write_image(source / "frame_1.jpg")

    module.prepare_dataset([source], output, allow_unlabeled=True)
    (source / "frame_1.jpg").unlink()

    summary = module.prepare_dataset([source], output, allow_unlabeled=True)

    assert summary.total_images == 1
    assert len(list(output.glob("images/*/*.jpg"))) == 1
    assert len(list(output.glob("labels/*/*.txt"))) == 1


def test_prepare_stage_b_dataset_extracts_video_keyframes(tmp_path: Path) -> None:
    module = load_prepare_module()
    video_path = tmp_path / "pilot.avi"
    output = tmp_path / "stage_b"
    write_video(video_path)

    summary = module.prepare_dataset(
        [video_path],
        output,
        allow_unlabeled=True,
        extract_videos=True,
        interval_seconds=1.0,
        min_scene_delta=30.0,
        blur_threshold=0.0,
    )

    assert summary.total_images == 3
    assert (output / "raw_keyframes" / "pilot").exists()
    assert len(list(output.glob("images/*/*.jpg"))) == 3
