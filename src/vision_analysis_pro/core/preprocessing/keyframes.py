"""OpenCV-based keyframe extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class KeyframeOptions:
    """Configuration for deterministic keyframe extraction."""

    interval_seconds: float = 1.0
    min_scene_delta: float = 0.0
    blur_threshold: float = 0.0
    max_frames: int | None = None
    output_dir: Path | None = None
    image_ext: str = "jpg"

    def validate(self) -> None:
        if self.interval_seconds < 0:
            raise ValueError("interval_seconds must be >= 0")
        if self.min_scene_delta < 0:
            raise ValueError("min_scene_delta must be >= 0")
        if self.blur_threshold < 0:
            raise ValueError("blur_threshold must be >= 0")
        if self.max_frames is not None and self.max_frames <= 0:
            raise ValueError("max_frames must be > 0")
        if not self.image_ext:
            raise ValueError("image_ext must not be empty")


@dataclass(frozen=True)
class ExtractedKeyframe:
    """A selected video frame and its extraction metadata."""

    frame_index: int
    timestamp_seconds: float
    reason: str
    scene_delta: float
    blur_score: float
    image: np.ndarray
    output_path: Path | None = None


def extract_keyframes(
    video_path: str | Path,
    options: KeyframeOptions | None = None,
) -> list[ExtractedKeyframe]:
    """Extract keyframes from a video with simple, explainable rules."""
    opts = options or KeyframeOptions()
    opts.validate()

    source_path = Path(video_path)
    if not source_path.exists():
        raise FileNotFoundError(f"video file does not exist: {source_path}")

    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        raise RuntimeError(f"unable to open video file: {source_path}")

    try:
        fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
        if fps <= 0:
            fps = 30.0

        interval_frames = (
            max(1, int(round(fps * opts.interval_seconds)))
            if opts.interval_seconds > 0
            else 0
        )

        if opts.output_dir is not None:
            opts.output_dir.mkdir(parents=True, exist_ok=True)

        keyframes: list[ExtractedKeyframe] = []
        previous_gray: np.ndarray | None = None
        frame_index = 0

        while True:
            success, frame = capture.read()
            if not success or frame is None:
                break

            gray_small = _small_gray(frame)
            scene_delta = (
                _mean_abs_delta(previous_gray, gray_small)
                if previous_gray is not None
                else 0.0
            )
            blur_score = _laplacian_variance(frame)
            reason = _selection_reason(
                frame_index=frame_index,
                interval_frames=interval_frames,
                scene_delta=scene_delta,
                min_scene_delta=opts.min_scene_delta,
            )
            previous_gray = gray_small

            if reason and blur_score >= opts.blur_threshold:
                timestamp_seconds = frame_index / fps
                output_path = _write_keyframe(frame, frame_index, opts)
                keyframes.append(
                    ExtractedKeyframe(
                        frame_index=frame_index,
                        timestamp_seconds=timestamp_seconds,
                        reason=reason,
                        scene_delta=scene_delta,
                        blur_score=blur_score,
                        image=frame.copy(),
                        output_path=output_path,
                    )
                )

                if opts.max_frames is not None and len(keyframes) >= opts.max_frames:
                    break

            frame_index += 1

        return keyframes
    finally:
        capture.release()


def _selection_reason(
    *,
    frame_index: int,
    interval_frames: int,
    scene_delta: float,
    min_scene_delta: float,
) -> str:
    if frame_index == 0:
        return "initial"
    if min_scene_delta > 0 and scene_delta >= min_scene_delta:
        return "scene_change"
    if interval_frames > 0 and frame_index % interval_frames == 0:
        return "interval"
    return ""


def _write_keyframe(
    frame: np.ndarray,
    frame_index: int,
    options: KeyframeOptions,
) -> Path | None:
    if options.output_dir is None:
        return None

    image_ext = options.image_ext.lower().lstrip(".")
    output_path = options.output_dir / f"frame_{frame_index:06d}.{image_ext}"
    if not cv2.imwrite(str(output_path), frame):
        raise RuntimeError(f"unable to write keyframe: {output_path}")
    return output_path


def _small_gray(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)


def _mean_abs_delta(previous: np.ndarray, current: np.ndarray) -> float:
    diff = cv2.absdiff(previous, current)
    return float(np.mean(diff))


def _laplacian_variance(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())
