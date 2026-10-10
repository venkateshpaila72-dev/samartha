"""File & Image Upload Endpoint for FarmShield.
Integrates Cloudinary for cloud asset storage with fallback to local upload storage.
"""

import os
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.integrations.cloudinary_client import CloudinaryClient
from app.schemas.common import APIResponse
from app.schemas.upload import ImageUploadOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/svg+xml",
}


@router.post("", response_model=APIResponse[ImageUploadOut])
async def upload_image(
    file: UploadFile = File(...),
    folder: Optional[str] = Form("farmshield/crops"),
    current_user: dict = Depends(get_current_user),
):
    """Uploads an image file to Cloudinary.
    Falls back to local directory if Cloudinary is not configured.
    """
    if not file.content_type or file.content_type.lower() not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {file.content_type}. Only standard images are supported.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # 1. Try Cloudinary if configured
    if CloudinaryClient.is_configured():
        try:
            result = CloudinaryClient.upload_image(
                file_bytes=file_bytes,
                filename=file.filename,
                folder=folder or "farmshield/crops",
            )
            return APIResponse(
                success=True,
                message="Image uploaded successfully to Cloudinary.",
                data=ImageUploadOut(
                    url=result["url"],
                    secure_url=result["secure_url"],
                    public_id=result.get("public_id"),
                    format=result.get("format"),
                    bytes=result.get("bytes"),
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
    extension = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex[:12]}.{extension}"
    target_path = os.path.join(upload_dir, filename)

    with open(target_path, "wb") as f:
        f.write(file_bytes)

    local_url = f"/static/uploads/{filename}"
    return APIResponse(
        success=True,
        message="Image saved locally (Cloudinary credentials not configured).",
        data=ImageUploadOut(
            url=local_url,
            secure_url=local_url,
            public_id=filename,
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
