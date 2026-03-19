import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HEX6 = re.compile(r"^#[0-9A-Fa-f]{6}$")


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    color: str = Field(default="#5dd9f7", description="CSS hex color e.g. #RRGGBB")

    @field_validator("color")
    @classmethod
    def color_hex(cls, v: str) -> str:
        if not _HEX6.match(v.strip()):
            raise ValueError("color must be a 6-digit hex string like #aabbcc")
        return v.strip()


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    color: Optional[str] = None

    @field_validator("color")
    @classmethod
    def color_hex(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not _HEX6.match(v.strip()):
            raise ValueError("color must be a 6-digit hex string like #aabbcc")
        return v.strip()


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    created_at: str
