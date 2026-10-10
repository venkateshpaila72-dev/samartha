"""Upload response schemas for FarmShield."""

from typing import Optional
from pydantic import BaseModel


class ImageUploadOut(BaseModel):
    url: str
    secure_url: str
    public_id: Optional[str] = None
    format: Optional[str] = None
    bytes: Optional[int] = None
    provider: str = "cloudinary"
    message: str = "Upload successful"
