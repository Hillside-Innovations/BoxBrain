from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CaptureDiagnostics(BaseModel):
    """Per-scan quality report."""
    frame_count: int
    brightness: float  # 0–1
    blur_score: float  # higher = sharper


class BoxCreate(BaseModel):
    label: str = Field(..., min_length=1, description="Box label e.g. attic_underscore_1")
    location_id: Optional[int] = None


class BoxUpdate(BaseModel):
    """PATCH body:

    - `location_id`: set/clear the saved location for this box (null clears).
    - `label`: rename the physical box (must remain unique).

    Omit keys you don't want to change.
    """

    label: Optional[str] = None
    location_id: Optional[int] = None


class BoxInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    location: Optional[str] = None
    created_at: str
    updated_at: str
    video_filename: Optional[str] = None


class BoxResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    location: Optional[str] = None
    location_id: Optional[int] = None
    location_color: Optional[str] = None
    created_at: str
    updated_at: str
    has_video: bool = False
    contents: List[str] = []  # detected items / frame descriptions from last scan
    diagnostics: Optional[CaptureDiagnostics] = None  # per-scan quality (frame count, brightness, blur)
