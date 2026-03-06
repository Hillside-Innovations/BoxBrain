"""Per-scan quality report: frame count, brightness, blur. Uses Pillow only."""
from pathlib import Path
from typing import List

from PIL import Image, ImageFilter, ImageStat


def _laplacian_variance(image: Image.Image) -> float:
    """Variance of Laplacian (3x3) on grayscale image. Higher = sharper."""
    gray = image.convert("L")
    # 3x3 Laplacian kernel
    kernel = [
        0, -1, 0,
        -1, 4, -1,
        0, -1, 0,
    ]
    lap = gray.filter(ImageFilter.Kernel((3, 3), kernel, scale=1, offset=0))
    stat = ImageStat.Stat(lap)
    return stat.variance[0]


def _mean_brightness(image: Image.Image) -> float:
    """Mean luminance 0–255."""
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    return stat.mean[0]


def compute_capture_diagnostics(frame_paths: List[Path]) -> dict:
    """
    Compute per-scan quality metrics from extracted frame paths.
    Returns dict with frame_count, brightness (0–1), blur_score (higher = sharper).
    """
    if not frame_paths:
        return {"frame_count": 0, "brightness": 0.0, "blur_score": 0.0}

    brightnesses: List[float] = []
    blur_scores: List[float] = []

    for path in frame_paths:
        if not path.exists():
            continue
        try:
            with Image.open(path) as img:
                img.load()
                bright = _mean_brightness(img)
                blur = _laplacian_variance(img)
                brightnesses.append(bright)
                blur_scores.append(blur)
        except Exception:
            continue

    # Only use frames where both metrics succeeded (avoid len(brightnesses) != len(blur_scores))
    if not brightnesses or len(brightnesses) != len(blur_scores):
        return {"frame_count": 0, "brightness": 0.0, "blur_score": 0.0}

    # brightness: normalize 0–255 -> 0–1 for API
    mean_bright = sum(brightnesses) / len(brightnesses)
    brightness_01 = round(mean_bright / 255.0, 4)
    # blur: mean of per-frame Laplacian variances (typical sharp frame ~100–1000+)
    mean_blur = sum(blur_scores) / len(blur_scores)

    return {
        "frame_count": len(frame_paths),
        "brightness": brightness_01,
        "blur_score": round(mean_blur, 2),
    }
