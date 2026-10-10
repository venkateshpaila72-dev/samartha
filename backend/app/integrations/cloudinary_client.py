"""Cloudinary Image and File Upload Integration for FarmShield.
Handles secure upload of crop photos, diary documentation, and storage receipts to Cloudinary.
"""

import logging
from typing import Optional, Dict, Any
import cloudinary
import cloudinary.uploader
from app.core.config import settings

logger = logging.getLogger(__name__)


class CloudinaryClient:
    """Manages asset uploads and transformations via Cloudinary."""

    _initialized = False

    @classmethod
    def _ensure_configured(cls) -> bool:
        """Configures Cloudinary SDK if credentials exist."""
        if not cls.is_configured():
            return False
        
        if not cls._initialized:
            try:
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_CLOUD_NAME.strip(),
                    api_key=settings.CLOUDINARY_API_KEY.strip(),
                    api_secret=settings.CLOUDINARY_API_SECRET.strip(),
                    secure=True,
                )
                cls._initialized = True
                logger.info("Cloudinary client initialized successfully.")
            except Exception as e:
                logger.error(f"Error configuring Cloudinary: {e}")
                return False
        return True

    @classmethod
    def is_configured(cls) -> bool:
        """Checks if required Cloudinary credentials are provided."""
        return bool(
            settings.CLOUDINARY_CLOUD_NAME.strip()
            and settings.CLOUDINARY_API_KEY.strip()
            and settings.CLOUDINARY_API_SECRET.strip()
        )

    @classmethod
    def upload_image(
        cls,
        file_bytes: bytes,
        filename: Optional[str] = None,
        folder: str = "farmshield/crops",
    ) -> Dict[str, Any]:
        """Uploads an image file to Cloudinary and returns media details.

        Args:
            file_bytes: Raw bytes of the image file.
            filename: Optional original filename.
            folder: Cloudinary asset folder.

        Returns:
            Dict containing secure_url, public_id, format, and upload metadata.
        """
        if not cls._ensure_configured():
            raise ValueError(
                "Cloudinary is not configured. Please supply CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in .env."
            )

        try:
            upload_params: Dict[str, Any] = {
                "folder": folder,
                "resource_type": "auto",
            }
            if filename:
                # Use public_id prefix if desired, or let Cloudinary assign unique ID
                clean_name = filename.rsplit(".", 1)[0].replace(" ", "_")
                upload_params["use_filename"] = True
                upload_params["unique_filename"] = True

            result = cloudinary.uploader.upload(file_bytes, **upload_params)
            logger.info(f"Image uploaded to Cloudinary: {result.get('public_id')}")

            return {
                "secure_url": result.get("secure_url") or result.get("url"),
                "url": result.get("secure_url") or result.get("url"),
                "public_id": result.get("public_id"),
                "format": result.get("format"),
                "bytes": result.get("bytes"),
                "width": result.get("width"),
                "height": result.get("height"),
                "provider": "cloudinary",
            }
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            raise RuntimeError(f"Cloudinary upload failed: {str(e)}")
