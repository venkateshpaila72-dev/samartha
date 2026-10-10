"""File & Image Upload Endpoint for FarmShield.
Integrates Cloudinary for cloud asset storage with fallback to local upload storage.
Enforces strict file type verification, size limits, and sanitization.
"""

import io
import os
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from PIL import Image

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.integrations.cloudinary_client import CloudinaryClient
from app.schemas.common import APIResponse
from app.schemas.upload import ImageUploadOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_FORMATS = {
    "jpeg": "jpg",
    "jpg": "jpg",
    "png": "png",
    "webp": "webp",
}

ALLOWED_FOLDERS = {
    "farmshield/crops",
    "farmshield/diary",
    "farmshield/general",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("", response_model=APIResponse[ImageUploadOut])
async def upload_image(
    file: UploadFile = File(...),
    folder: Optional[str] = Form("farmshield/crops"),
    current_user: dict = Depends(get_current_user),
):
    """Uploads an image file to Cloudinary.
    Falls back to local directory if Cloudinary is not configured.
    Enforces strict magic byte/Pillow verification, 5MB max size, and safe server-side filenames.
    """
    if not file.content_type or file.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {file.content_type}. Only JPEG, PNG, and WebP images are supported.",
        )

    # Read at most one byte beyond the limit so oversized uploads are rejected without
    # buffering an arbitrarily large request body in application memory.
    file_bytes = await file.read(MAX_FILE_SIZE + 1)
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    # Validate image bytes and determine true image format
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img.verify()
            raw_format = (img.format or "").lower()
            if raw_format not in ALLOWED_FORMATS:
                raise ValueError(f"Unsupported format: {raw_format}")
            extension = ALLOWED_FORMATS[raw_format]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, spoofed, or corrupted image content. Only valid JPEG, PNG, and WebP files are accepted.",
        )

    # Restrict folder to allow-list
    target_folder = folder if folder in ALLOWED_FOLDERS else "farmshield/crops"

    # Server-generated safe filename
    safe_filename = f"{uuid.uuid4().hex}.{extension}"

    # 1. Try Cloudinary if configured
    if CloudinaryClient.is_configured():
        try:
            result = CloudinaryClient.upload_image(
                file_bytes=file_bytes,
                filename=safe_filename,
                folder=target_folder,
            )
            return APIResponse(
                success=True,
                message="Image uploaded successfully to Cloudinary.",
                data=ImageUploadOut(
                    url=result["url"],
                    secure_url=result["secure_url"],
                    public_id=result.get("public_id"),
                    format=result.get("format", extension),
                    bytes=result.get("bytes", len(file_bytes)),
                    provider="cloudinary",
                    message="Image hosted securely on Cloudinary.",
                ),
            )
        except Exception as e:
            logger.error(f"Cloudinary upload error: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cloudinary upload failed: {str(e)}",
            )

    # 2. Local fallback if Cloudinary credentials are not present
    upload_dir = settings.STORAGE_UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    target_path = os.path.join(upload_dir, safe_filename)

    with open(target_path, "wb") as f:
        f.write(file_bytes)

    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    absolute_url = f"{base_url}/static/uploads/{safe_filename}"

    return APIResponse(
        success=True,
        message="Image saved locally (Cloudinary credentials not configured).",
        data=ImageUploadOut(
            url=absolute_url,
            secure_url=absolute_url,
            public_id=safe_filename,
            format=extension,
            bytes=len(file_bytes),
            provider="local_fallback",
            message="Saved locally. Configure Cloudinary in .env for production cloud hosting.",
        ),
    )


@router.get("/status")
def get_storage_status(current_user: dict = Depends(get_current_user)):
    """Diagnostic check for upload storage provider."""
    is_cloud = CloudinaryClient.is_configured()
    return APIResponse(
        success=True,
        message="Storage status retrieved.",
        data={
            "provider": "cloudinary" if is_cloud else "local_fallback",
            "cloudinary_configured": is_cloud,
            "cloud_name": settings.CLOUDINARY_CLOUD_NAME if is_cloud else None,
            "upload_folder": "farmshield/crops",
        },
    )
