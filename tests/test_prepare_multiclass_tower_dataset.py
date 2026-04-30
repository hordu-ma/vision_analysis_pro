"""Tests for preparing the multiclass tower-defect YOLO dataset."""

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
    script_path = Path("scripts/prepare_multiclass_tower_dataset.py")
    spec = importlib.util.spec_from_file_location(
        "prepare_multiclass_tower_dataset",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_image(path: Path) -> None:
    image = np.full((80, 100, 3), 180, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def write_inbox_item(
    inbox: Path,
    *,
    stem: str,
    class_id: int,
    class_name: str,
) -> None:
    raw_images = inbox / "raw_images"
    labels = inbox / "reviewed_labels"
    metadata = inbox / "metadata"
    raw_images.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)
    metadata.mkdir(parents=True, exist_ok=True)
    write_image(raw_images / f"{stem}.jpg")
    (labels / f"{stem}.txt").write_text(
        f"{class_id} 0.500000 0.500000 0.250000 0.250000\n",
        encoding="utf-8",
    )
    (metadata / f"{stem}.json").write_text(
        json.dumps(
            {
                "proposed_class_id": class_id,
                "proposed_class_name": class_name,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_prepare_multiclass_tower_dataset_writes_yolo_dataset(
    tmp_path: Path,
) -> None:
    module = load_prepare_module()
    inbox = tmp_path / "inbox"
    output = tmp_path / "dataset"
    for class_id, class_name in module.CLASSES.items():
        write_inbox_item(
            inbox,
            stem=f"{class_name}_001",
            class_id=class_id,
            class_name=class_name,
        )

    summary = module.prepare_dataset(
        inbox,
        output,
        train_ratio=0.5,
        val_ratio=0.25,
        test_ratio=0.25,
    )

    assert summary.total_images == 4
    assert summary.total_boxes == 4
    assert (output / "data.yaml").exists()
    assert (output / "manifest.json").exists()

    with (output / "data.yaml").open("r", encoding="utf-8") as f:
        data_config = yaml.safe_load(f)
    assert data_config["nc"] == 4
    assert data_config["names"] == module.CLASSES

    with (output / "manifest.json").open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["split_counts"] == {"train": 2, "val": 1, "test": 1}
    assert manifest["total_boxes"] == 4


def test_prepare_multiclass_tower_dataset_requires_reviewed_labels(
    tmp_path: Path,
) -> None:
    module = load_prepare_module()
    inbox = tmp_path / "inbox"
    raw_images = inbox / "raw_images"
    labels = inbox / "reviewed_labels"
    raw_images.mkdir(parents=True)
    labels.mkdir(parents=True)
    write_image(raw_images / "deformation_001.jpg")

    with pytest.raises(FileNotFoundError, match="missing reviewed label"):
        module.prepare_dataset(inbox, tmp_path / "dataset")


def test_prepare_multiclass_tower_dataset_rejects_bad_class(
    tmp_path: Path,
) -> None:
    module = load_prepare_module()
    inbox = tmp_path / "inbox"
    write_inbox_item(
        inbox,
        stem="bad_001",
        class_id=0,
        class_name="deformation",
    )
    (inbox / "reviewed_labels" / "bad_001.txt").write_text(
        "9 0.500000 0.500000 0.250000 0.250000\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid class"):
        module.prepare_dataset(inbox, tmp_path / "dataset")
