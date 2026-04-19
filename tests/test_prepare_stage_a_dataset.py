"""Tests for preparing the Stage A crack-only YOLO dataset."""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import yaml


def load_prepare_module():
    script_path = Path("scripts/prepare_stage_a_crack_dataset.py")
    spec = importlib.util.spec_from_file_location("prepare_stage_a_crack_dataset", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_coco_zip(source: Path, split: str) -> None:
    archive_path = source / "data" / f"{split}.zip"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    coco = {
        "images": [
            {"id": 1, "file_name": "positive.jpg", "width": 100, "height": 50},
            {"id": 2, "file_name": "negative.jpg", "width": 100, "height": 50},
        ],
        "annotations": [
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [10, 5, 40, 20]},
            {"id": 2, "image_id": 2, "category_id": 2, "bbox": [0, 0, 20, 10]},
        ],
        "categories": [
            {"id": 1, "name": "crack"},
            {"id": 2, "name": "mold"},
        ],
    }
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("_annotations.coco.json", json.dumps(coco))
        zf.writestr("positive.jpg", b"positive")
        zf.writestr("negative.jpg", b"negative")


def test_prepare_stage_a_dataset_converts_coco_to_crack_only_yolo(tmp_path: Path) -> None:
    module = load_prepare_module()
    source = tmp_path / "source"
    output = tmp_path / "stage_a_crack"
    write_coco_zip(source, "train")
    write_coco_zip(source, "valid")

    summaries = module.prepare_dataset(
        source,
        output,
        crack_names={"crack"},
        negative_ratio=1.0,
        include_negatives=True,
    )

    assert {summary.split for summary in summaries} == {"train", "val"}
    assert (output / "images/train/positive.jpg").exists()
    assert (output / "images/train/negative.jpg").exists()
    assert (output / "labels/train/negative.txt").read_text(encoding="utf-8") == ""

    label = (output / "labels/train/positive.txt").read_text(encoding="utf-8").strip()
    assert label == "0 0.300000 0.300000 0.400000 0.400000"

    with (output / "data.yaml").open("r", encoding="utf-8") as f:
        data_config = yaml.safe_load(f)
    assert data_config["nc"] == 1
    assert data_config["names"] == {0: "crack"}

    with (output / "manifest.json").open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["target"]["classes"] == ["crack"]
