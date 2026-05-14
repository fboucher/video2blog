#!/usr/bin/env python3
"""CLI entry point for keyframe extraction.

Moved from keyframe_extractor.py so the library module is purely programmatic.
"""

import argparse
import os
import sys
from pathlib import Path

from keyframe_extractor import extract_keyframes, ExtractionProgress


def _progress_callback(p: ExtractionProgress) -> None:
    """Print progress to stdout for CLI use."""
    print(
        f"[{p.status:>10}] frame {p.frame:>6}/{p.total_frames:<6} | scene {p.scene:<3}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract keyframes from video files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract keyframes using scene detection
  %(prog)s video.mp4 -o ./frames -t 0.3 -m 50

  # Extract keyframes at 30-second intervals
  %(prog)s video.mp4 --strategy interval --interval-seconds 30 -o ./frames

  # Extract frames at specific timestamps
  %(prog)s video.mp4 --strategy timestamp --timestamps 10.5,25.0,60.3 -o ./frames

  # Extract 5 frames per timestamp
  %(prog)s video.mp4 --strategy timestamp --timestamps 10.5,25.0 --frames-per-point 5 -o ./frames
        """,
    )
    parser.add_argument("video_path", help="Path to the input video file")
    parser.add_argument(
        "-o", "--output", default="./keyframes", help="Output directory for keyframes"
    )
    parser.add_argument(
        "--strategy",
        choices=["scene", "interval", "timestamp"],
        default="scene",
        help="Extraction strategy (default: scene)",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=0.3,
        help="Scene detection threshold (0.0-1.0, default: 0.3)",
    )
    parser.add_argument(
        "-m",
        "--max-frames",
        type=int,
        default=100,
        help="Maximum number of keyframes to extract (default: 100)",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=30,
        help="Seconds between extractions for interval strategy (default: 30)",
    )
    parser.add_argument(
        "--frames-per-point",
        type=int,
        default=3,
        help="Frames to extract around each point (default: 3)",
    )
    parser.add_argument(
        "--timestamps",
        type=str,
        help='Comma-separated list of timestamps, e.g., "10.5,25.0,60.3"',
    )
    parser.add_argument(
        "--frame-sampling",
        type=int,
        default=5,
        help="Process every Nth frame during scene detection (default: 5)",
    )

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.video_path):
        print(f"Error: Video file not found: {args.video_path}")
        return 1

    # Parse timestamps if provided
    timestamps = None
    if args.timestamps:
        try:
            timestamps = [float(ts.strip()) for ts in args.timestamps.split(",")]
        except ValueError:
            print(
                "Error: Invalid timestamp format. "
                "Use comma-separated numbers (e.g., '10.5,25.0,60.3')"
            )
            return 1

    # Validate threshold
    if args.strategy == "scene" and not 0.0 <= args.threshold <= 1.0:
        print("Error: Threshold must be between 0.0 and 1.0")
        return 1

    # Validate frames-per-point
    if args.frames_per_point < 1:
        print("Error: frames-per-point must be at least 1")
        return 1

    try:
        results = extract_keyframes(
            video_path=args.video_path,
            output_dir=args.output,
            strategy=args.strategy,
            threshold=args.threshold,
            interval_seconds=args.interval_seconds,
            frames_per_interval=args.frames_per_point,
            timestamps=timestamps,
            max_keyframes=args.max_frames,
            frame_sampling_interval=args.frame_sampling,
            on_progress=_progress_callback,
        )
        print(f"\nExtraction complete! Saved {len(results)} keyframes to {args.output}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
