"""Extract keyframes from a video with OpenCV."""

import argparse
from pathlib import Path

from vision_analysis_pro.core.preprocessing.keyframes import (
    KeyframeOptions,
    extract_keyframes,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract keyframes from a video")
    parser.add_argument("video", help="Input video path")
    parser.add_argument(
        "--output-dir",
        default="data/keyframes",
        help="Directory for extracted frames",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=1.0,
        help="Fixed extraction interval in seconds",
    )
    parser.add_argument(
        "--min-scene-delta",
        type=float,
        default=0.0,
        help="Mean absolute grayscale delta required for scene-change selection",
    )
    parser.add_argument(
        "--blur-threshold",
        type=float,
        default=0.0,
        help="Minimum Laplacian variance required to keep a frame",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Maximum number of frames to extract",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frames = extract_keyframes(
        args.video,
        KeyframeOptions(
            interval_seconds=args.interval_seconds,
            min_scene_delta=args.min_scene_delta,
            blur_threshold=args.blur_threshold,
            max_frames=args.max_frames,
            output_dir=Path(args.output_dir),
        ),
    )

    print(f"extracted {len(frames)} keyframes")
    for frame in frames:
        print(
            f"{frame.frame_index}\t{frame.timestamp_seconds:.3f}s\t"
            f"{frame.reason}\t{frame.output_path}"
        )


if __name__ == "__main__":
    main()
