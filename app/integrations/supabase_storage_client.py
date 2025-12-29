"""Supabase Storage client integration for PDF uploads"""

import asyncio
from typing import BinaryIO
from uuid import uuid4
from supabase import create_client, Client
from app.core.config import settings


def get_supabase_client() -> Client:
    """Get Supabase client instance"""
    if not settings.SUPABASE_URL:
        raise ValueError("SUPABASE_URL is not configured. Please set SUPABASE_URL in your .env file")
    
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is not configured. Please set SUPABASE_SERVICE_ROLE_KEY in your .env file")
    
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


async def upload_pdf(
    file: BinaryIO,
    folder_path: str,
    file_name: str
) -> dict:
    """
    Upload a PDF file to Supabase Storage.
    
    Args:
        file: Binary file object to upload
        folder_path: Path to folder in storage (e.g., "Class 11/Physics/Chapter 1")
        file_name: Name of the file to upload
    
    Returns:
        Dictionary with file_path and public_url
    
    Raises:
        Exception: If upload fails
    """
    try:
        # Read file content
        file.seek(0)
        file_content = file.read()
        
        def _upload():
            supabase = get_supabase_client()
            bucket_name = settings.SUPABASE_STORAGE_BUCKET
            
            if not bucket_name:
                raise ValueError("SUPABASE_STORAGE_BUCKET is not configured. Please set SUPABASE_STORAGE_BUCKET in your .env file")
            
            # Create file path: folder_path/file_name
            # Add UUID to filename to avoid conflicts
            file_extension = file_name.split('.')[-1] if '.' in file_name else 'pdf'
            file_base_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
            unique_file_name = f"{file_base_name}_{uuid4().hex[:8]}.{file_extension}"
            
            # Construct full path
            file_path = f"{folder_path}/{unique_file_name}" if folder_path else unique_file_name
            
            # Upload file to Supabase Storage
            supabase.storage.from_(bucket_name).upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": "application/pdf",
                    "upsert": False  # Don't overwrite existing files
                }
            )
            
            # Get public URL
            public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
            
            return {
                'file_path': file_path,
                'file_id': file_path,  # Use file_path as ID for consistency
                'web_view_link': public_url,
                'web_content_link': public_url
            }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _upload)
    except Exception as e:
        raise Exception(f"Failed to upload PDF to Supabase Storage: {str(e)}")


async def delete_pdf(file_path: str) -> bool:
    """
    Delete a PDF file from Supabase Storage.
    
    Args:
        file_path: The file path in Supabase Storage (stored as file_id in database)
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        def _delete():
            supabase = get_supabase_client()
            bucket_name = settings.SUPABASE_STORAGE_BUCKET
            
            if not bucket_name:
                raise ValueError("SUPABASE_STORAGE_BUCKET is not configured")
            
            # Delete file from Supabase Storage
            supabase.storage.from_(bucket_name).remove([file_path])
            return True
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _delete)
        return True
    except Exception as e:
        # If file doesn't exist, consider it deleted
        if "not found" in str(e).lower() or "404" in str(e):
            return True
        return False

