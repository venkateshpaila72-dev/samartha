"""Authentication Endpoints."""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    Token,
    UserLogin,
    UserOut,
    UserRegister,
    UserUpdate,
)
from app.schemas.common import APIResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=APIResponse[Token])
async def register(payload: UserRegister):
    existing = UserRepository.get_by_email(payload.email)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    user_id = f"user_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    user_doc = {
        "id": user_id,
        "email": payload.email.strip().lower(),
        "password_hash": hash_password(payload.password),
        "full_name": payload.full_name,
        "role": "farmer",
        "preferred_language": payload.preferred_language,
        "phone_number": payload.phone_number,
        "village_or_location": payload.village_or_location,
        "whatsapp_url": payload.whatsapp_url,
        "created_at": now_iso,
    }

    UserRepository.create(user_doc)

    user_out = UserOut(**user_doc)
    token = create_access_token(
        data={"sub": user_id, "role": "farmer"}
    )

    return APIResponse(
        success=True,
        message="Registration successful.",
        data=Token(
            access_token=token,
            token_type="bearer",
            user=user_out,
        ),
    )


@router.post("/login", response_model=APIResponse[Token])
async def login(payload: UserLogin):
    user = UserRepository.get_by_email(payload.email)

    if not user or not verify_password(
        payload.password,
        user.get("password_hash", ""),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    actual_role = user.get("role", "farmer")

    if actual_role != payload.login_as:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"This account is not registered for "
                f"{payload.login_as} login."
            ),
        )

    user_out = UserOut(**user)
    token = create_access_token(
        data={"sub": user["id"], "role": actual_role}
    )

    return APIResponse(
        success=True,
        message="Login successful.",
        data=Token(
            access_token=token,
            token_type="bearer",
            user=user_out,
        ),
    )


@router.get("/me", response_model=APIResponse[UserOut])
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
):
    return APIResponse(
        success=True,
        message="User profile retrieved.",
        data=UserOut(**current_user),
    )


@router.patch("/me", response_model=APIResponse[UserOut])
async def update_profile(
    payload: UserUpdate,
    current_user: dict = Depends(get_current_user),
):
    updates = {
        key: value
        for key, value in payload.model_dump().items()
        if value is not None
    }

    updated = UserRepository.update(current_user["id"], updates)

    return APIResponse(
        success=True,
        message="Profile updated successfully.",
        data=UserOut(**updated),
    )


@router.post("/logout", response_model=APIResponse[dict])
async def logout(
    current_user: dict = Depends(get_current_user),
):
    return APIResponse(
        success=True,
        message="Logged out successfully.",
        data={"user_id": current_user["id"]},
    )