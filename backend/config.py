"""Local-first config: paths and feature flags. No cloud required."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _base_dir() -> Path:
    return Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Paths (local storage under backend/data)
    data_dir: Path = _base_dir() / "data"
    db_path: Path = _base_dir() / "data" / "boxbrain.db"
    chroma_path: Path = _base_dir() / "data" / "chroma"
    uploads_dir: Path = _base_dir() / "data" / "uploads"
    frames_dir: Path = _base_dir() / "data" / "frames"

    # Vision: use real BLIP model; set MOCK_VISION=1 to skip model download for testing
    mock_vision: bool = False

    # Max video upload size (bytes). Phones can produce large files; 100MB is a safe default.
    max_upload_bytes: int = 100 * 1024 * 1024

    # Search / ranking tuning
    # Minimum box-level similarity score [0,1] required to return a hit.
    search_min_score: float = 0.7
    # Top result must beat the second-best by at least this margin, otherwise treat as "no confident match".
    search_min_score_delta: float = 0.05
    # Require at least this many strong frame-level matches within a box to consider it a hit.
    search_min_frames: int = 2
    # Per-frame score threshold [0,1] for counting a frame as a "strong" match.
    search_frame_score_threshold: float = 0.6
    # If a box has at least one frame with this score or higher, it qualifies even with fewer strong frames (e.g. label-only match).
    search_strong_match_score: float = 0.9

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
