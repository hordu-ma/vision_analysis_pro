"""Tests for preparing the multiclass prototype inbox."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest


def load_prepare_module():
    script_path = Path("scripts/prepare_multiclass_prototype_inbox.py")
    spec = importlib.util.spec_from_file_location(
        "prepare_multiclass_prototype_inbox",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_image(path: Path) -> None:
    image = np.full((64, 80, 3), 160, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def test_prepare_multiclass_inbox_writes_metadata_and_queue(
    tmp_path: Path,
) -> None:
    module = load_prepare_module()
    source = tmp_path / "source"
    output = tmp_path / "multiclass_inbox"
    for folder_name in module.CLASS_MAPPING:
        class_dir = source / folder_name
        class_dir.mkdir(parents=True)
        write_image(class_dir / "sample.jpg")

    summary = module.prepare_inbox(source, output)

    assert summary.total_images == 4
    assert summary.class_counts == {
        "deformation": 1,
        "tower_corrosion": 1,
        "loose_bolt": 1,
        "bolt_rust": 1,
    }
    assert (output / "raw_images" / "deformation_001.jpg").exists()
    assert (output / "reviewed_labels").is_dir()
    assert (output / "annotation_queue.csv").exists()
    assert (output / "classes.json").exists()
    assert (output / "manifest.json").exists()

    metadata = json.loads(
        (output / "metadata" / "deformation_001.json").read_text(encoding="utf-8")
    )
    assert metadata["proposed_class_id"] == 0
    assert metadata["proposed_class_name"] == "deformation"
    assert metadata["review_status"] == "pending_bbox_annotation"
    assert metadata["width"] == 80
    assert metadata["height"] == 64


def test_prepare_multiclass_inbox_rejects_missing_source(tmp_path: Path) -> None:
    module = load_prepare_module()

    with pytest.raises(FileNotFoundError, match="source directory does not exist"):
        module.prepare_inbox(tmp_path / "missing", tmp_path / "output")


def test_prepare_multiclass_inbox_rejects_unreadable_image(
    tmp_path: Path,
) -> None:
    module = load_prepare_module()
    source = tmp_path / "source" / "变形"
    source.mkdir(parents=True)
    (source / "bad.jpg").write_text("not an image", encoding="utf-8")

    with pytest.raises(ValueError, match="not a readable image"):
        module.prepare_inbox(tmp_path / "source", tmp_path / "output")
