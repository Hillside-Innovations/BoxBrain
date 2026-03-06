"""Extract image frames from uploaded video using ffmpeg. Local CLI, no cloud."""
import subprocess
from pathlib import Path
from typing import List

from config import settings


class VideoProcessor:
    def __init__(self) -> None:
        self.frames_dir = settings.frames_dir

    def extract_frames(self, video_path: Path, box_id: int, max_frames: int = 10) -> List[Path]:
        """Extract up to max_frames from video; save under data/frames/{box_id}/. Returns paths."""
        out_dir = self.frames_dir / str(box_id)
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
        subprocess.run(cmd, check=True, capture_output=True)
        frames = sorted(out_dir.glob("frame_*.jpg"))
        return frames
