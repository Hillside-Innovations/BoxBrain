"""Extract image frames from uploaded video using ffmpeg. Local CLI, no cloud."""
import subprocess
from pathlib import Path
from typing import List, Optional

from config import settings


class VideoProcessor:
    def __init__(self) -> None:
        self.frames_dir = settings.frames_dir

    def extract_frames(
        self,
        video_path: Path,
        box_id: int,
        max_frames: int = 10,
        out_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Extract up to max_frames from video; save under out_dir or data/frames/{box_id}/. Returns paths."""
        out_dir = out_dir or (self.frames_dir / str(box_id))
        out_dir.mkdir(parents=True, exist_ok=True)
        # ffmpeg: 1 frame per second (or spread over duration), max max_frames
        # -i input, -vf fps=1 (1 per sec), -vframes N
        out_pattern = str(out_dir / "frame_%03d.jpg")
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vf", "fps=1",
            "-vframes", str(max_frames),
            "-q:v", "2",
            out_pattern,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Install ffmpeg and add it to your PATH. "
                "On Windows: install from https://ffmpeg.org/download.html or via winget (winget install ffmpeg), then restart the server."
            ) from None
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode(errors="replace").strip() or "(no stderr)"
            raise RuntimeError(f"ffmpeg failed: {stderr}") from e
        # Only return frames that exist and have content (ffmpeg can write 0-byte files on some codecs)
        frames = sorted(p for p in out_dir.glob("frame_*.jpg") if p.exists() and p.stat().st_size > 0)
        if not frames:
            raise RuntimeError(
                "ffmpeg produced no valid frames. The video may be too short, unsupported, or corrupt. "
                "Try a 5–10 second MP4 or MOV from your phone."
            )
        return frames
