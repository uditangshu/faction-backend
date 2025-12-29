"""Google Drive client integration for PDF uploads"""

import asyncio
import io
from typing import BinaryIO, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

from app.core.config import settings


def get_drive_service():
    """Get Google Drive service instance"""
    if not settings.GOOGLE_DRIVE_CREDENTIALS_PATH:
        raise ValueError("Google Drive credentials path is not configured. Please set GOOGLE_DRIVE_CREDENTIALS_PATH in your .env file")
    
    credentials = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_DRIVE_CREDENTIALS_PATH,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    
    return build('drive', 'v3', credentials=credentials)


async def upload_pdf(
    file: BinaryIO,
    folder_path: str,
    file_name: str
) -> dict:
    """
    Upload a PDF file to Google Drive.
    
    Args:
        file: Binary file object to upload
        folder_path: Path to folder in Google Drive (e.g., "Class 11/Physics/Chapter 1")
        file_name: Name of the file to upload
    
    Returns:
        Dictionary with file_id and web_view_link
    
    Raises:
        Exception: If upload fails
    """
    try:
        # Read file content
        file.seek(0)
        file_content = file.read()
        
        def _upload():
            drive_service = get_drive_service()
            
            # Create folder structure if it doesn't exist
            folder_id = _get_or_create_folder(drive_service, folder_path)
            
            # Create file metadata
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            # Upload file
            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype='application/pdf',
                resumable=True
            )
            
            file_obj = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            # Make file accessible (viewable by anyone with link)
            drive_service.permissions().create(
                fileId=file_obj['id'],
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()
            
            return {
                'file_id': file_obj['id'],
                'web_view_link': file_obj.get('webViewLink', ''),
                'web_content_link': file_obj.get('webContentLink', '')
            }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _upload)
    except HttpError as e:
        raise Exception(f"Failed to upload PDF to Google Drive: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to upload PDF: {str(e)}")


async def delete_pdf(file_id: str) -> bool:
    """
    Delete a PDF file from Google Drive.
    
    Args:
        file_id: The Google Drive file ID
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        def _delete():
            drive_service = get_drive_service()
            drive_service.files().delete(fileId=file_id).execute()
            return True
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _delete)
        return True
    except HttpError as e:
        if e.resp.status == 404:
            return False
        return False
    except Exception:
        return False


def _get_or_create_folder(drive_service, folder_path: str) -> str:
    """
    Get or create folder structure in Google Drive.
    
    Args:
        drive_service: Google Drive service instance
        folder_path: Path to folder (e.g., "Class 11/Physics/Chapter 1")
    
    Returns:
        Folder ID
    """
    parts = [part.strip() for part in folder_path.split('/') if part.strip()]
    parent_id = 'root'
    
    for folder_name in parts:
        # Escape single quotes in folder name for query
        escaped_name = folder_name.replace("'", "\\'")
        # Check if folder exists
        query = f"name='{escaped_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
        results = drive_service.files().list(q=query, fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            parent_id = items[0]['id']
        else:
            # Create folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            parent_id = folder['id']
    
    return parent_id

