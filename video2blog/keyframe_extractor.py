#!/usr/bin/env python3
"""Keyframe extraction library with progress callback support.

This module provides a clean programmatic API for extracting keyframes from
video files.  CLI entry point has been moved to cli.py.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Literal, Dict

import cv2
import numpy as np


# ── Types ─────────────────────────────────────────────────────────────────────

ExtractionStrategy = Literal["scene", "interval", "timestamp"]


@dataclass
class ExtractionProgress:
    """Progress report emitted during keyframe extraction."""

    frame: int
    total_frames: int
    scene: int
    status: Literal["detecting", "extracting", "done"]


# ── Public API ──────────────────────────────────────────────────────────────


def extract_keyframes(
    video_path: str | Path,
    output_dir: str | Path,
    strategy: ExtractionStrategy = "scene",
    threshold: float = 0.3,
    interval_seconds: int = 30,
    frames_per_interval: int = 3,
    timestamps: List[float] | None = None,
    max_keyframes: int = 100,
    frame_sampling_interval: int = 5,
    jpeg_quality: int = 90,
    on_progress: Callable[[ExtractionProgress], None] | None = None,
) -> List[Dict[str, Any]]:
    """Extract keyframes from a video file.

    Args:
        video_path: Path to the input video file.
        output_dir: Directory to save extracted keyframes.
        strategy: Extraction strategy - "scene" (detect scene changes),
            "interval" (extract at regular intervals), or "timestamp"
            (extract at specific timestamps).
        threshold: Scene detection threshold (0.0-1.0). Lower values detect
            more scenes. Only used with strategy="scene". Default is 0.3.
        interval_seconds: Seconds between extractions for interval strategy.
            Default is 30.
        frames_per_interval: Number of frames to extract around each interval
            point (centered). Default is 3.
        timestamps: List of timestamps (in seconds) for timestamp strategy.
            Required when strategy="timestamp".
        max_keyframes: Maximum number of keyframes to extract across all
            strategies. Default is 100.
        frame_sampling_interval: Process every Nth frame during scene
            detection to improve performance. Only used with strategy="scene".
            Default is 5.
        jpeg_quality: JPEG compression quality (0-100). Default is 90.
        on_progress: Optional callback called after each keyframe is saved.
            Receives an ExtractionProgress dataclass.

    Returns:
        List of dictionaries containing frame metadata:
        {frame_number, timestamp, filename, path}.

    Raises:
        ValueError: If video file cannot be opened, threshold is out of range,
            or timestamps are invalid.
        IOError: If output directory cannot be created.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Early validation of strategy-specific parameters
    if strategy == "scene" and not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0.0 and 1.0")
    if strategy == "interval" and interval_seconds < 1:
        raise ValueError("interval_seconds must be at least 1")
    if strategy == "timestamp" and timestamps is None:
        raise ValueError("timestamps is required when strategy='timestamp'")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0.0

    _emit_progress(on_progress, 0, total_frames, 0, "detecting")

    if strategy == "scene":
        results = _extract_scene(
            cap=cap,
            output_dir=output_dir,
            fps=fps,
            total_frames=total_frames,
            threshold=threshold,
            max_keyframes=max_keyframes,
            frame_sampling_interval=frame_sampling_interval,
            jpeg_quality=jpeg_quality,
            on_progress=on_progress,
        )
    elif strategy == "interval":
        results = _extract_interval(
            cap=cap,
            output_dir=output_dir,
            fps=fps,
            total_frames=total_frames,
            duration=duration,
            interval_seconds=interval_seconds,
            frames_per_interval=frames_per_interval,
            max_keyframes=max_keyframes,
            jpeg_quality=jpeg_quality,
            on_progress=on_progress,
        )
    elif strategy == "timestamp":
        results = _extract_timestamp(
            cap=cap,
            output_dir=output_dir,
            fps=fps,
            total_frames=total_frames,
            duration=duration,
            timestamps=timestamps,
            frames_per_timestamp=frames_per_interval,
            max_keyframes=max_keyframes,
            jpeg_quality=jpeg_quality,
            on_progress=on_progress,
        )
    else:
        cap.release()
        raise ValueError(f"Unknown strategy: {strategy}")

    cap.release()

    _emit_progress(
        on_progress,
        total_frames,
        total_frames,
        len(results),
        "done",
    )

    # Save metadata
    metadata_path = output_dir / "keyframes_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(
            {
                "video_path": str(video_path),
                "total_frames": total_frames,
                "duration": duration,
                "fps": fps,
                "strategy": strategy,
                "keyframes_extracted": len(results),
                "threshold": threshold if strategy == "scene" else None,
                "interval_seconds": interval_seconds
                if strategy == "interval"
                else None,
                "timestamps": timestamps if strategy == "timestamp" else None,
                "keyframes": results,
            },
            f,
            indent=2,
        )

    return results


def detect_keyframe_timestamps(
    video_path: str | Path,
    threshold: float = 0.3,
    max_keyframes: int = 100,
    frame_sampling_interval: int = 5,
) -> list[float]:
    """Detect scene-change timestamps without extracting frames.

    Uses the same histogram-based scene detection as
    strategy="scene" but returns only the timestamps, no files.

    Args:
        video_path: Path to the input video file.
        threshold: Scene detection threshold (0.0-1.0). Default is 0.3.
        max_keyframes: Maximum number of timestamps to return. Default is 100.
        frame_sampling_interval: Process every Nth frame. Default is 5.

    Returns:
        List of timestamps (in seconds) where scene changes were detected.

    Raises:
        ValueError: If video file cannot be opened or threshold is invalid.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0.0 and 1.0")

    video_path = Path(video_path)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    prev_frame = None
    frame_count = 0
    saved_count = 0
    timestamps: list[float] = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % frame_sampling_interval != 0:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_frame is not None:
            hist_current = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist_prev = cv2.calcHist([prev_frame], [0], None, [256], [0, 256])
            cv2.normalize(
                hist_current, hist_current, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX
            )
            cv2.normalize(
                hist_prev, hist_prev, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX
            )
            hist_diff = cv2.compareHist(hist_prev, hist_current, cv2.HISTCMP_CORREL)

            if hist_diff < (1 - threshold) and saved_count < max_keyframes:
                timestamps.append(frame_count / fps)
                saved_count += 1

        prev_frame = gray

        if saved_count >= max_keyframes:
            break

    cap.release()
    return timestamps


# ── Internal helpers ──────────────────────────────────────────────────────────


def _emit_progress(
    on_progress: Callable[[ExtractionProgress], None] | None,
    frame: int,
    total_frames: int,
    scene: int,
    status: Literal["detecting", "extracting", "done"],
) -> None:
    if on_progress is not None:
        on_progress(ExtractionProgress(frame, total_frames, scene, status))


def _save_frame(
    frame: Any,
    output_dir: Path,
    filename: str,
    jpeg_quality: int,
) -> Path:
    output_path = output_dir / filename
    cv2.imwrite(str(output_path), frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    return output_path


def _extract_scene(
    cap: Any,
    output_dir: Path,
    fps: float,
    total_frames: int,
    threshold: float,
    max_keyframes: int,
    frame_sampling_interval: int,
    jpeg_quality: int,
    on_progress: Callable[[ExtractionProgress], None] | None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    prev_frame = None
    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Sample every Nth frame for performance
        if frame_count % frame_sampling_interval != 0:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_frame is not None:
            hist_current = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist_prev = cv2.calcHist([prev_frame], [0], None, [256], [0, 256])
            cv2.normalize(
                hist_current, hist_current, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX
            )
            cv2.normalize(
                hist_prev, hist_prev, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX
            )
            hist_diff = cv2.compareHist(hist_prev, hist_current, cv2.HISTCMP_CORREL)

            if hist_diff < (1 - threshold) and saved_count < max_keyframes:
                timestamp = frame_count / fps
                filename = f"keyframe_{saved_count:04d}_t{timestamp:.2f}s.jpg"
                output_path = _save_frame(frame, output_dir, filename, jpeg_quality)

                results.append(
                    {
                        "frame_number": frame_count,
                        "timestamp": timestamp,
                        "filename": filename,
                        "path": str(output_path),
                    }
                )
                saved_count += 1
                _emit_progress(
                    on_progress, frame_count, total_frames, saved_count, "extracting"
                )

        prev_frame = gray

        if saved_count >= max_keyframes:
            break

    return results


def _extract_interval(
    cap: Any,
    output_dir: Path,
    fps: float,
    total_frames: int,
    duration: float,
    interval_seconds: int,
    frames_per_interval: int,
    max_keyframes: int,
    jpeg_quality: int,
    on_progress: Callable[[ExtractionProgress], None] | None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    offset = (frames_per_interval - 1) // 2

    # Generate interval points
    interval_points = []
    t = 0.0
    while t <= duration and len(interval_points) * frames_per_interval < max_keyframes:
        interval_points.append(t)
        t += interval_seconds

    saved_count = 0
    for interval_idx, timestamp in enumerate(interval_points):
        center_frame = int(timestamp * fps)

        for i in range(-offset, frames_per_interval - offset):
            if saved_count >= max_keyframes:
                break

            target_frame = center_frame + i
            if target_frame < 0 or target_frame >= total_frames:
                continue

            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if not ret:
                continue

            actual_timestamp = target_frame / fps
            offset_label = f"{i:+d}" if i != 0 else "exact"
            filename = (
                f"frame_int{interval_idx:03d}_{timestamp:.2f}s"
                f"_{offset_label}_f{target_frame:06d}.jpg"
            )
            output_path = _save_frame(frame, output_dir, filename, jpeg_quality)

            results.append(
                {
                    "frame_number": target_frame,
                    "timestamp": actual_timestamp,
                    "filename": filename,
                    "path": str(output_path),
                }
            )
            saved_count += 1
            _emit_progress(
                on_progress, target_frame, total_frames, saved_count, "extracting"
            )

        if saved_count >= max_keyframes:
            break

    return results


def _extract_timestamp(
    cap: Any,
    output_dir: Path,
    fps: float,
    total_frames: int,
    duration: float,
    timestamps: List[float],
    frames_per_timestamp: int,
    max_keyframes: int,
    jpeg_quality: int,
    on_progress: Callable[[ExtractionProgress], None] | None,
) -> List[Dict[str, Any]]:
    for ts in timestamps:
        if ts < 0 or ts > duration:
            raise ValueError(
                f"Timestamp {ts:.2f}s is out of range (0.0-{duration:.2f}s)"
            )

    results: List[Dict[str, Any]] = []
    offset = (frames_per_timestamp - 1) // 2
    saved_count = 0

    for ts_idx, timestamp in enumerate(timestamps):
        if saved_count >= max_keyframes:
            break

        center_frame = int(timestamp * fps)

        for i in range(-offset, frames_per_timestamp - offset):
            if saved_count >= max_keyframes:
                break

            target_frame = center_frame + i
            if target_frame < 0 or target_frame >= total_frames:
                continue

            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if not ret:
                continue

            actual_timestamp = target_frame / fps
            offset_label = f"{i:+d}" if i != 0 else "exact"
            filename = (
                f"frame_ts{ts_idx:03d}_{timestamp:.2f}s"
                f"_{offset_label}_f{target_frame:06d}.jpg"
            )
            output_path = _save_frame(frame, output_dir, filename, jpeg_quality)

            results.append(
                {
                    "frame_number": target_frame,
                    "timestamp": actual_timestamp,
                    "filename": filename,
                    "path": str(output_path),
                }
            )
            saved_count += 1
            _emit_progress(
                on_progress, target_frame, total_frames, saved_count, "extracting"
            )

    return results
