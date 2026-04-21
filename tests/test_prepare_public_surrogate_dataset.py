"""Tests for preparing a public surrogate crack-only YOLO dataset."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml


def load_prepare_module():
    script_path = Path("scripts/prepare_public_surrogate_crack_dataset.py")
    spec = importlib.util.spec_from_file_location(
        "prepare_public_surrogate_crack_dataset",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((80, 120, 3), 128, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def write_pascal_voc_annotation(path: Path, *, labels: list[tuple[str, tuple[int, int, int, int]]]) -> None:
    objects = "\n".join(
        (
            "<object>"
            f"<name>{label}</name>"
            "<pose>Unspecified</pose>"
            "<truncated>0</truncated>"
            "<difficult>0</difficult>"
            "<bndbox>"
            f"<xmin>{bbox[0]}</xmin>"
            f"<ymin>{bbox[1]}</ymin>"
            f"<xmax>{bbox[2]}</xmax>"
            f"<ymax>{bbox[3]}</ymax>"
            "</bndbox>"
            "</object>"
        )
        for label, bbox in labels
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "<annotation>"
            "<folder>images</folder>"
            f"<filename>{path.stem}.jpg</filename>"
            "<size><width>120</width><height>80</height><depth>3</depth></size>"
            "<segmented>0</segmented>"
            f"{objects}"
            "</annotation>"
        ),
        encoding="utf-8",
    )


def test_prepare_public_surrogate_dataset_builds_crack_only_output(tmp_path: Path) -> None:
    module = load_prepare_module()
    sdnet_source = tmp_path / "SDNET2018"
    rdd_source = tmp_path / "RDD2022"
    output = tmp_path / "stage_b_public"

    write_image(sdnet_source / "BridgeDeck" / "NonCrack" / "deck_negative.jpg")
    write_image(sdnet_source / "Wall" / "Crack" / "wall_positive.jpg")

    write_image(rdd_source / "Japan" / "images" / "road_crack.jpg")
    write_pascal_voc_annotation(
        rdd_source / "Japan" / "annotations" / "road_crack.xml",
        labels=[("D00", (12, 10, 60, 40))],
    )

    write_image(rdd_source / "India" / "images" / "road_pothole.jpg")
    write_pascal_voc_annotation(
        rdd_source / "India" / "annotations" / "road_pothole.xml",
        labels=[("D40", (20, 12, 40, 36))],
    )

    prepared = module.prepare_dataset(
        output,
        sdnet2018_source=sdnet_source,
        rdd2022_source=rdd_source,
        train_ratio=0.5,
        val_ratio=0.25,
        test_ratio=0.25,
    )

    assert prepared.total_images == 3
    assert prepared.labeled_images == 1
    assert prepared.empty_label_images == 2
    assert prepared.source_summary["sdnet2018"]["reviewed_negative_images"] == 1
    assert prepared.source_summary["sdnet2018"]["skipped_crack_images_without_labels"] == 1
    assert prepared.source_summary["rdd2022"]["labeled_crack_images"] == 1
    assert prepared.source_summary["rdd2022"]["reviewed_negative_images"] == 1

    with (output / "data.yaml").open("r", encoding="utf-8") as f:
        data_config = yaml.safe_load(f)
    assert data_config["nc"] == 1
    assert data_config["names"] == {0: "crack"}

    with (output / "manifest.json").open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["target"]["mode"] == "public_surrogate"
    assert manifest["annotation_status"]["labeled_images"] == 1
    assert manifest["annotation_status"]["reviewed_negative_empty_label_images"] == 2
    assert manifest["source_summary"]["sdnet2018"]["reviewed_negative_images"] == 1
    assert manifest["source_summary"]["rdd2022"]["labeled_crack_images"] == 1


def test_parse_rdd2022_xml_maps_multiple_crack_classes(tmp_path: Path) -> None:
    module = load_prepare_module()
    annotation = tmp_path / "road.xml"
    write_pascal_voc_annotation(
        annotation,
        labels=[
            ("D00", (10, 10, 50, 30)),
            ("D20", (60, 15, 100, 35)),
            ("D40", (20, 20, 30, 30)),
        ],
    )

    lines = module.parse_rdd2022_xml(annotation, crack_classes={"D00", "D10", "D20"})

    assert len(lines) == 2
    assert all(line.startswith("0 ") for line in lines)
