"""Supabase Storage client integration for PDF uploads"""

import asyncio
import httpx
from typing import BinaryIO
from uuid import uuid4
from app.core.config import settings


def get_storage_url() -> str:
    """Get Supabase Storage API URL"""
    if not settings.SUPABASE_URL:
        raise ValueError("SUPABASE_URL is not configured. Please set SUPABASE_URL in your .env file")
    
    # Remove trailing slash and construct storage URL
    base_url = settings.SUPABASE_URL.rstrip('/')
    return f"{base_url}/storage/v1"


def get_auth_headers() -> dict:
    """Get authentication headers for Supabase Storage"""
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is not configured. Please set SUPABASE_SERVICE_ROLE_KEY in your .env file")
    
    return {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    }


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
            bucket_name = settings.SUPABASE_STORAGE_BUCKET
            
            if not bucket_name:
                raise ValueError("SUPABASE_STORAGE_BUCKET is not configured. Please set SUPABASE_STORAGE_BUCKET in your .env file")
            
            # Create file path: folder_path/file_name
            # Add UUID to filename to avoid conflicts
            file_extension = file_name.split('.')[-1] if '.' in file_name else 'pdf'
            file_base_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
            unique_file_name = f"{file_base_name}_{uuid4().hex[:8]}.{file_extension}"
            
            # Construct full path (URL encode the path)
            import urllib.parse
            if folder_path:
                # URL encode each part of the path
                encoded_parts = [urllib.parse.quote(part, safe='') for part in folder_path.split('/')]
                encoded_folder = '/'.join(encoded_parts)
                file_path = f"{encoded_folder}/{urllib.parse.quote(unique_file_name, safe='')}"
            else:
                file_path = urllib.parse.quote(unique_file_name, safe='')
            
            storage_url = get_storage_url()
            headers = get_auth_headers()
            
            # Upload file using direct HTTP API
            upload_url = f"{storage_url}/object/{bucket_name}/{file_path}"
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    upload_url,
                    headers=headers,
                    files={
                        'file': (unique_file_name, file_content, 'application/pdf')
                    },
                    data={
                        'content-type': 'application/pdf',
                        'upsert': 'false'
                    }
                )
                response.raise_for_status()
            
            # Construct public URL
            base_url = settings.SUPABASE_URL.rstrip('/')
            public_url = f"{base_url}/storage/v1/object/public/{bucket_name}/{file_path}"
            
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
            bucket_name = settings.SUPABASE_STORAGE_BUCKET
            
            if not bucket_name:
                raise ValueError("SUPABASE_STORAGE_BUCKET is not configured")
            
            storage_url = get_storage_url()
            headers = get_auth_headers()
            
            # Delete file using direct HTTP API
            delete_url = f"{storage_url}/object/{bucket_name}/{file_path}"
            
            with httpx.Client(timeout=30.0) as client:
                response = client.delete(delete_url, headers=headers)
                # 404 means file doesn't exist, which is fine
                if response.status_code == 404:
                    return True
                response.raise_for_status()
            
            return True
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _delete)
        return True
    except Exception as e:
        # If file doesn't exist, consider it deleted
        if "not found" in str(e).lower() or "404" in str(e):
            return True
        return False

