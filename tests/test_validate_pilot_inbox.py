"""Tests for validating the Stage B pilot inbox handoff."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np


def load_validate_module():
    script_path = Path("scripts/validate_pilot_inbox.py")
    spec = importlib.util.spec_from_file_location("validate_pilot_inbox", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_image(path: Path) -> None:
    image = np.full((64, 64, 3), 128, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def write_metadata(path: Path, **overrides: object) -> None:
    data = {
        "asset_id": "tower-001",
        "device_id": "edge-001",
        "site_name": "north-line",
        "capture_time": "2026-04-26T10:00:00+08:00",
        "source_type": "image_folder",
        "reviewer": "qa",
        "review_rule_version": "docs/annotation_guidelines.md#v1.0",
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_inbox(tmp_path: Path) -> Path:
    root = tmp_path / "pilot_inbox"
    (root / "raw_images").mkdir(parents=True)
    (root / "reviewed_labels").mkdir()
    (root / "metadata").mkdir()
    return root


def test_validate_pilot_inbox_accepts_reviewed_positive_sample(
    tmp_path: Path,
) -> None:
    module = load_validate_module()
    root = make_inbox(tmp_path)
    write_image(root / "raw_images" / "frame_001.jpg")
    (root / "reviewed_labels" / "frame_001.txt").write_text(
        "0 0.500000 0.500000 0.250000 0.250000\n",
        encoding="utf-8",
    )
    write_metadata(root / "metadata" / "frame_001.json")

    summary = module.validate_pilot_inbox(root)

    assert summary.ready_for_he007 is True
    assert summary.total_images == 1
    assert summary.reviewed_positive_images == 1
    assert summary.reviewed_positive_boxes == 1
    assert summary.errors == ()


def test_validate_pilot_inbox_requires_metadata_for_each_image(
    tmp_path: Path,
) -> None:
    module = load_validate_module()
    root = make_inbox(tmp_path)
    write_image(root / "raw_images" / "frame_001.jpg")
    (root / "reviewed_labels" / "frame_001.txt").write_text(
        "0 0.500000 0.500000 0.250000 0.250000\n",
        encoding="utf-8",
    )

    summary = module.validate_pilot_inbox(root)

    assert summary.ready_for_he007 is False
    assert any("missing metadata for raw image" in error for error in summary.errors)


def test_validate_pilot_inbox_rejects_no_positive_by_default(
    tmp_path: Path,
) -> None:
    module = load_validate_module()
    root = make_inbox(tmp_path)
    write_image(root / "raw_images" / "negative_001.jpg")
    (root / "reviewed_labels" / "negative_001.txt").write_text("", encoding="utf-8")
    write_metadata(root / "metadata" / "negative_001.json")

    summary = module.validate_pilot_inbox(root)

    assert summary.reviewed_negative_images == 1
    assert summary.ready_for_he007 is False
    assert any("no reviewed positive crack boxes" in error for error in summary.errors)


def test_validate_pilot_inbox_allows_structure_only_mode(
    tmp_path: Path,
) -> None:
    module = load_validate_module()
    root = make_inbox(tmp_path)
    write_image(root / "raw_images" / "negative_001.jpg")
    (root / "reviewed_labels" / "negative_001.txt").write_text("", encoding="utf-8")
    write_metadata(root / "metadata" / "negative_001.json")

    summary = module.validate_pilot_inbox(root, require_positive=False)

    assert summary.errors == ()
    assert summary.ready_for_he007 is False
    assert summary.reviewed_negative_images == 1


def test_validate_pilot_inbox_supports_metadata_items_manifest(
    tmp_path: Path,
) -> None:
    module = load_validate_module()
    root = make_inbox(tmp_path)
    write_image(root / "raw_images" / "frame_001.jpg")
    (root / "reviewed_labels" / "frame_001.txt").write_text(
        "0 0.500000 0.500000 0.250000 0.250000\n",
        encoding="utf-8",
    )
    write_metadata(
        root / "metadata" / "manifest.json",
        items=[
            {
                "image": "frame_001.jpg",
                "asset_id": "tower-001",
                "device_id": "edge-001",
                "site_name": "north-line",
                "capture_time": "2026-04-26T10:00:00+08:00",
                "source_type": "image_folder",
                "reviewer": "qa",
                "review_rule_version": "docs/annotation_guidelines.md#v1.0",
            }
        ],
    )

    summary = module.validate_pilot_inbox(root)

    assert summary.ready_for_he007 is True
    assert summary.metadata_records == 1
