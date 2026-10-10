"""Authentication Schemas."""

from typing import Optional
from pydantic import BaseModel, Field

EMAIL_PATTERN = r"^[\w\.\+\-]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,}$"


class UserRegister(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, description="Valid email address")
    password: str = Field(min_length=6, description="Password with minimum 6 characters")
    full_name: str = Field(min_length=2)
    role: str = Field(default="farmer", pattern="^(farmer|admin|expert)$")
    preferred_language: str = Field(default="en")
    phone_number: Optional[str] = None
    village_or_location: Optional[str] = None


class UserLogin(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str


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
    created_at: Optional[str] = None



class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    preferred_language: Optional[str] = None
    phone_number: Optional[str] = None
    village_or_location: Optional[str] = None


Token.model_rebuild()
