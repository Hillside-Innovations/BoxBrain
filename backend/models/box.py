from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BoxCreate(BaseModel):
    label: str = Field(..., min_length=1, description="Box label e.g. attic_underscore_1")
    location: Optional[str] = None


class BoxUpdate(BaseModel):
    location: Optional[str] = None


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
    created_at: str
    updated_at: str
    has_video: bool = False
    contents: list[str] = []  # detected items / frame descriptions from last scan
