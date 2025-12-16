"""Cloudinary client integration for image uploads"""

import asyncio
import io
import cloudinary
import cloudinary.uploader
from typing import BinaryIO

from app.core.config import settings


def configure_cloudinary() -> None:
    """Configure Cloudinary with credentials from settings"""
    if not all([
        settings.CLOUDINARY_CLOUD_NAME,
        settings.CLOUDINARY_API_KEY,
        settings.CLOUDINARY_API_SECRET
    ]):
        raise ValueError("Cloudinary credentials are not configured. Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in your .env file")

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,  # Use HTTPS
    )


async def upload_image(file: BinaryIO, folder: str = "avatars", public_id: str | None = None) -> str:
    """
    Upload an image file to Cloudinary.
    
    Args:
        file: Binary file object to upload
        folder: Cloudinary folder to store the image (default: "avatars")
        public_id: Optional custom public ID for the image (default: auto-generated)
    
    Returns:
        The secure URL of the uploaded image
        
    Raises:
        Exception: If upload fails
    """
    # Configure Cloudinary if not already configured
    try:
        configure_cloudinary()
    except ValueError:
        # If configuration fails, raise it
        raise

    # Read file content into memory (reset file pointer first)
    file.seek(0)
    file_content = file.read()

    # Upload options
    upload_options = {
        "folder": folder,
        "resource_type": "image",
        "transformation": [
            {"width": 400, "height": 400, "crop": "fill", "gravity": "face"},
            {"quality": "auto"},
            {"fetch_format": "auto"}
        ],
    }

    if public_id:
        upload_options["public_id"] = public_id

    try:
        # Upload the file (run in executor since cloudinary is synchronous)
        # Use BytesIO to wrap the content for thread safety
        file_obj = io.BytesIO(file_content)
        
        def _upload():
            return cloudinary.uploader.upload(file_obj, **upload_options)
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _upload)
        
        # Return the secure URL
        return result.get("secure_url", result.get("url", ""))
    except Exception as e:
        raise Exception(f"Failed to upload image to Cloudinary: {str(e)}")


async def delete_image(public_id: str) -> bool:
    """
    Delete an image from Cloudinary.
    
    Args:
        public_id: The public ID of the image to delete (including folder path)
        
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        configure_cloudinary()
        
        # Run in executor since cloudinary is synchronous
        def _delete():
            return cloudinary.uploader.destroy(public_id, resource_type="image")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _delete)
        return result.get("result") == "ok"
    except Exception:
        return False

