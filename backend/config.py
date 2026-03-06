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

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
