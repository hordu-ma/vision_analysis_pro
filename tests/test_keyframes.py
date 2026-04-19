"""Tests for OpenCV keyframe extraction."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from vision_analysis_pro.core.preprocessing.keyframes import (
    KeyframeOptions,
    extract_keyframes,
)


def _create_test_video(path: Path, *, fps: float = 2.0) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (64, 64))
    assert writer.isOpened()
    try:
        for value in [0, 0, 255, 255, 128]:
            frame = np.full((64, 64, 3), value, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def test_extract_keyframes_by_interval_and_scene_change(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.avi"
    _create_test_video(video_path)

    frames = extract_keyframes(
        video_path,
        KeyframeOptions(interval_seconds=1.0, min_scene_delta=30.0),
    )

    assert [frame.frame_index for frame in frames] == [0, 2, 4]
    assert frames[0].reason == "initial"
    assert frames[1].reason == "scene_change"
    assert frames[2].reason == "scene_change"
    assert frames[1].timestamp_seconds == pytest.approx(1.0)


def test_extract_keyframes_writes_selected_frames(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.avi"
    output_dir = tmp_path / "keyframes"
    _create_test_video(video_path)

    frames = extract_keyframes(
        video_path,
        KeyframeOptions(interval_seconds=1.0, output_dir=output_dir, max_frames=2),
    )

    assert len(frames) == 2
    assert all(frame.output_path is not None for frame in frames)
    assert sorted(path.name for path in output_dir.glob("*.jpg")) == [
        "frame_000000.jpg",
        "frame_000002.jpg",
    ]


def test_extract_keyframes_validates_options(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.avi"
    _create_test_video(video_path)

    with pytest.raises(ValueError, match="interval_seconds"):
        extract_keyframes(video_path, KeyframeOptions(interval_seconds=-1.0))


def test_extract_keyframes_rejects_missing_video(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_keyframes(tmp_path / "missing.avi")
