"""
Tests for keyframe_extractor.py — Issue #57 acceptance criteria.

All cv2 / numpy calls are mocked; no real video files or OpenCV installation
is required.  conftest.py injects MagicMocks for cv2 and numpy before import.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import keyframe_extractor
from keyframe_extractor import ExtractionProgress, extract_keyframes

# cv2 is a MagicMock injected by conftest.py
import cv2


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_cap_mock(total_frames=300, fps=30.0):
    """Build a VideoCapture-like mock."""
    cap = MagicMock()
    cap.isOpened.return_value = True

    def _get(prop):
        return {
            cv2.CAP_PROP_FPS: fps,
            cv2.CAP_PROP_FRAME_COUNT: total_frames,
            cv2.CAP_PROP_POS_FRAMES: 0,
        }.get(prop, 0)

    cap.get.side_effect = _get

    frame_counter = [0]

    def _read():
        if frame_counter[0] < total_frames:
            frame_counter[0] += 1
            return (True, MagicMock())
        return (False, None)

    cap.read.side_effect = _read
    cap.set.return_value = True
    return cap


@pytest.fixture(autouse=True)
def _reset_cv2_mocks():
    """Clear any side-effects / return-values set by previous tests."""
    cv2.reset_mock()
    for attr in (
        "VideoCapture",
        "compareHist",
        "calcHist",
        "cvtColor",
        "normalize",
        "imwrite",
    ):
        getattr(cv2, attr).side_effect = None
        getattr(cv2, attr).return_value = MagicMock()
    yield


# ── Scene strategy ───────────────────────────────────────────────────────────


def test_scene_strategy_extracts_keyframes(tmp_path):
    cap = _make_cap_mock(total_frames=300, fps=30.0)
    cv2.VideoCapture.return_value = cap

    call_idx = [0]

    def _compareHist(h1, h2, method):
        call_idx[0] += 1
        return 0.5 if call_idx[0] % 12 == 0 else 0.95

    cv2.compareHist.side_effect = _compareHist
    cv2.calcHist.return_value = MagicMock()
    cv2.cvtColor.return_value = MagicMock()

    results = extract_keyframes(
        video_path="fake.mp4",
        output_dir=tmp_path,
        strategy="scene",
        threshold=0.3,
        max_keyframes=10,
        frame_sampling_interval=5,
    )

    assert len(results) > 0
    assert all("frame_number" in r for r in results)
    assert all("timestamp" in r for r in results)
    assert all("filename" in r for r in results)
    assert all("path" in r for r in results)
    assert cv2.VideoCapture.called


def test_scene_strategy_respects_max_keyframes(tmp_path):
    cap = _make_cap_mock(total_frames=1000, fps=30.0)
    cv2.VideoCapture.return_value = cap
    cv2.compareHist.return_value = 0.1  # Always different
    cv2.calcHist.return_value = MagicMock()
    cv2.cvtColor.return_value = MagicMock()

    results = extract_keyframes(
        video_path="fake.mp4",
        output_dir=tmp_path,
        strategy="scene",
        threshold=0.3,
        max_keyframes=5,
        frame_sampling_interval=1,
    )

    assert len(results) == 5


def test_scene_strategy_invalid_threshold(tmp_path):
    with pytest.raises(ValueError, match="threshold must be between"):
        extract_keyframes(
            video_path="fake.mp4",
            output_dir=tmp_path,
            strategy="scene",
            threshold=1.5,
        )


# ── Interval strategy ────────────────────────────────────────────────────────


def test_interval_strategy_extracts_at_intervals(tmp_path):
    cap = _make_cap_mock(total_frames=300, fps=30.0)  # 10 seconds
    cv2.VideoCapture.return_value = cap

    results = extract_keyframes(
        video_path="fake.mp4",
        output_dir=tmp_path,
        strategy="interval",
        interval_seconds=2,
        frames_per_interval=1,
        max_keyframes=100,
    )

    assert len(results) == 5


def test_interval_strategy_respects_max_keyframes(tmp_path):
    cap = _make_cap_mock(total_frames=600, fps=30.0)  # 20 seconds
    cv2.VideoCapture.return_value = cap

    results = extract_keyframes(
        video_path="fake.mp4",
        output_dir=tmp_path,
        strategy="interval",
        interval_seconds=1,
        frames_per_interval=3,
        max_keyframes=6,
    )

    # interval 0 produces only 2 frames (t=-1 is out of bounds),
    # interval 1 produces 3 frames → total 5
    assert len(results) == 5


# ── Timestamp strategy ─────────────────────────────────────────────────────────


def test_timestamp_strategy_extracts_at_given_points(tmp_path):
    cap = _make_cap_mock(total_frames=300, fps=30.0)  # 10 seconds
    cv2.VideoCapture.return_value = cap

    results = extract_keyframes(
        video_path="fake.mp4",
        output_dir=tmp_path,
        strategy="timestamp",
        timestamps=[2.0, 5.0, 8.0],
        frames_per_interval=1,
        max_keyframes=100,
    )

    assert len(results) == 3


def test_timestamp_strategy_invalid_timestamp(tmp_path):
    cap = _make_cap_mock(total_frames=300, fps=30.0)  # 10 seconds
    cv2.VideoCapture.return_value = cap

    with pytest.raises(ValueError, match="out of range"):
        extract_keyframes(
            video_path="fake.mp4",
            output_dir=tmp_path,
            strategy="timestamp",
            timestamps=[2.0, 15.0],  # 15s > 10s duration
            max_keyframes=100,
        )


# ── Progress callback ────────────────────────────────────────────────────────


def test_progress_callback_fires(tmp_path):
    cap = _make_cap_mock(total_frames=300, fps=30.0)
    cv2.VideoCapture.return_value = cap
    cv2.compareHist.side_effect = [0.5 if i % 12 == 0 else 0.95 for i in range(300)]
    cv2.calcHist.return_value = MagicMock()
    cv2.cvtColor.return_value = MagicMock()

    progress_calls = []

    def _callback(p):
        progress_calls.append(p)

    extract_keyframes(
        video_path="fake.mp4",
        output_dir=tmp_path,
        strategy="scene",
        threshold=0.3,
        max_keyframes=10,
        frame_sampling_interval=5,
        on_progress=_callback,
    )

    assert len(progress_calls) > 0
    assert all(isinstance(p, ExtractionProgress) for p in progress_calls)
    assert progress_calls[-1].status == "done"


# ── Metadata ───────────────────────────────────────────────────────────────────


def test_metadata_json_saved(tmp_path):
    cap = _make_cap_mock(total_frames=60, fps=30.0)
    cv2.VideoCapture.return_value = cap
    cv2.compareHist.return_value = 0.5  # Always different
    cv2.calcHist.return_value = MagicMock()
    cv2.cvtColor.return_value = MagicMock()

    extract_keyframes(
        video_path="fake.mp4",
        output_dir=tmp_path,
        strategy="scene",
        threshold=0.3,
        max_keyframes=5,
    )

    metadata_path = tmp_path / "keyframes_metadata.json"
    assert metadata_path.exists()
    data = json.loads(metadata_path.read_text())
    assert data["strategy"] == "scene"
    assert data["keyframes_extracted"] > 0


# ── Error handling ─────────────────────────────────────────────────────────────


def test_unreadable_video_raises(tmp_path):
    cap = MagicMock()
    cap.isOpened.return_value = False
    cv2.VideoCapture.return_value = cap

    with pytest.raises(ValueError, match="Unable to open video file"):
        extract_keyframes(
            video_path="nonexistent.mp4",
            output_dir=tmp_path,
            strategy="scene",
        )


def test_timestamp_without_timestamps_raises(tmp_path):
    with pytest.raises(ValueError, match="timestamps is required"):
        extract_keyframes(
            video_path="fake.mp4",
            output_dir=tmp_path,
            strategy="timestamp",
        )
