"""Unit tests for VisionService (mock vision only in CI)."""
import pytest
from pathlib import Path

from services.vision import VisionService, _FALLBACK_CAPTION


def test_describe_frames_empty_paths():
    """Empty frame list returns empty descriptions."""
    vs = VisionService()
    assert vs.describe_frames([]) == []


def test_describe_frames_mock_vision():
    """With MOCK_VISION=1 we get one caption per frame."""
    vs = VisionService()
    # Pass non-existent paths; mock doesn't read them
    paths = [Path("/nonexistent/frame_001.jpg"), Path("/nonexistent/frame_002.jpg")]
    result = vs.describe_frames(paths)
    assert len(result) == 2
    assert "frame 1" in result[0] and "frame 2" in result[1]


def test_fallback_caption_defined():
    """Fallback caption used when a frame fails or BLIP returns empty."""
    assert _FALLBACK_CAPTION == "box contents"
