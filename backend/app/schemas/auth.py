"""Authentication Schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

EMAIL_PATTERN = r"^[\w\.\+\-]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,}$"


class UserRegister(BaseModel):
    email: str = Field(
        pattern=EMAIL_PATTERN,
        description="Valid email address",
    )
    password: str = Field(
        min_length=6,
        description="Password with minimum 6 characters",
    )
    full_name: str = Field(min_length=2)
    preferred_language: str = Field(default="en", pattern="^(en|hi|te|ta|kn|mr|pa|bn)$")
    phone_number: Optional[str] = None
    village_or_location: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    selected_crop: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    whatsapp_url: Optional[str] = None


class UserLogin(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str
    login_as: Literal["farmer", "admin"] = "farmer"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    preferred_language: str
    phone_number: Optional[str] = None
    village_or_location: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    selected_crop: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_market_sync_at: Optional[str] = None
    last_market_sync_summary: Optional[dict] = None
    whatsapp_url: Optional[str] = None
    created_at: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    preferred_language: Optional[str] = Field(default=None, pattern="^(en|hi|te|ta|kn|mr|pa|bn)$")
    phone_number: Optional[str] = None
    village_or_location: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    selected_crop: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_market_sync_at: Optional[str] = None
    last_market_sync_summary: Optional[dict] = None
    whatsapp_url: Optional[str] = None


Token.model_rebuild()