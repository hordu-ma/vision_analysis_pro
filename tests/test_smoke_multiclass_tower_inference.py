"""Tests for the multiclass tower inference smoke helper."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def load_smoke_module():
    script_path = Path("scripts/smoke_multiclass_tower_inference.py")
    spec = importlib.util.spec_from_file_location(
        "smoke_multiclass_tower_inference",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_class_names_accepts_expected_mapping() -> None:
    module = load_smoke_module()

    module._validate_class_names(
        {
            0: "deformation",
            1: "tower_corrosion",
            2: "loose_bolt",
            3: "bolt_rust",
        }
    )


def test_validate_class_names_accepts_string_keys() -> None:
    module = load_smoke_module()

    module._validate_class_names(
        {
            "0": "deformation",
            "1": "tower_corrosion",
            "2": "loose_bolt",
            "3": "bolt_rust",
        }
    )


def test_validate_class_names_rejects_unexpected_mapping() -> None:
    module = load_smoke_module()

    with pytest.raises(ValueError, match="unexpected model class mapping"):
        module._validate_class_names(
            {
                0: "crack",
                1: "tower_corrosion",
                2: "loose_bolt",
                3: "bolt_rust",
            }
        )
