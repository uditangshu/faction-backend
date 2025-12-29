"""Notes endpoints"""

from uuid import UUID
from fastapi import APIRouter, Query, File, UploadFile, Form
from typing import Optional

from app.api.v1.dependencies import NotesServiceDep, CurrentUser
from app.schemas.notes import (
    NotesResponse,
    NotesListResponse,
)
from app.integrations.google_drive_client import upload_pdf, delete_pdf
from app.exceptions.http_exceptions import NotFoundException, BadRequestException
from app.models.Basequestion import Subject, Chapter
from sqlalchemy import select

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.post("/", response_model=NotesResponse, status_code=201)
async def upload_note(
    notes_service: NotesServiceDep,
    current_user: CurrentUser,
    chapter_id: UUID = Form(..., description="Chapter ID"),
    subject_id: UUID = Form(..., description="Subject ID"),
    pdf_file: UploadFile = File(..., description="PDF file to upload"),
) -> NotesResponse:
    """Upload a new note PDF"""
    try:
        # Validate file type
        if not pdf_file.content_type or pdf_file.content_type != 'application/pdf':
            raise BadRequestException("File must be a PDF")
        
        # Validate chapter and subject belong to user's class
        db = notes_service.db
        
        # Check subject belongs to user's class
        subject_result = await db.execute(
            select(Subject).where(
                Subject.id == subject_id,
                Subject.class_id == current_user.class_id
            )
        )
        subject = subject_result.scalar_one_or_none()
        if not subject:
            raise BadRequestException("Subject not found or does not belong to your class")
        
        # Check chapter belongs to subject
        chapter_result = await db.execute(
            select(Chapter).where(
                Chapter.id == chapter_id,
                Chapter.subject_id == subject_id
            )
        )
        chapter = chapter_result.scalar_one_or_none()
        if not chapter:
            raise BadRequestException("Chapter not found or does not belong to the subject")
        
        # Create folder path: Class/Subject/Chapter
        class_name = subject.subject_class_lvl.name if subject.subject_class_lvl else f"Class_{current_user.class_id}"
        subject_name = subject.subject_type.value
        chapter_name = chapter.name
        
        folder_path = f"{class_name}/{subject_name}/{chapter_name}"
        
        # Upload PDF to Google Drive
        try:
            upload_result = await upload_pdf(
                pdf_file.file,
                folder_path=folder_path,
                file_name=pdf_file.filename or "note.pdf"
            )
        except Exception as e:
            raise BadRequestException(f"Failed to upload PDF: {str(e)}")
        
        # Create the note
        note = await notes_service.create_note(
            chapter_id=chapter_id,
            subject_id=subject_id,
            file_name=pdf_file.filename or "note.pdf",
            file_id=upload_result['file_id'],
            web_view_link=upload_result['web_view_link'],
            web_content_link=upload_result.get('web_content_link'),
        )
        
        return NotesResponse.model_validate(note)
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to upload note: {str(e)}")


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: UUID,
    notes_service: NotesServiceDep,
    current_user: CurrentUser,
) -> None:
    """Delete a note"""
    # Get the note first to extract the file_id for deletion from Google Drive
    note = await notes_service.get_note_by_id(note_id)
    if not note:
        raise NotFoundException(f"Note with ID {note_id} not found")
    
    # Verify note belongs to user's class
    db = notes_service.db
    
    subject_result = await db.execute(
        select(Subject).where(
            Subject.id == note.subject_id,
            Subject.class_id == current_user.class_id
        )
    )
    subject = subject_result.scalar_one_or_none()
    if not subject:
        raise NotFoundException(f"Note with ID {note_id} not found")
    
    # Delete the file from Google Drive
    if note.file_id:
        try:
            await delete_pdf(note.file_id)
        except Exception:
            # Log error but continue with database deletion
            pass
    
    # Delete from database
    deleted = await notes_service.delete_note(note_id)
    if not deleted:
        raise NotFoundException(f"Note with ID {note_id} not found")


@router.get("/", response_model=NotesListResponse)
async def get_notes(
    notes_service: NotesServiceDep,
    current_user: CurrentUser,
    class_id: UUID = Query(..., description="Class ID to filter notes"),
    subject_id: Optional[UUID] = Query(None, description="Filter by subject ID"),
    chapter_id: Optional[UUID] = Query(None, description="Filter by chapter ID"),
    sort_order: str = Query("latest", description="Sort order: 'latest' or 'oldest'"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records"),
) -> NotesListResponse:
    """
    Get notes filtered by class_id, optionally by subject and chapter.
    
    The notes are automatically filtered by the provided class_id. You can further filter by:
    - subject_id: Filter by specific subject
    - chapter_id: Filter by specific chapter (requires subject_id to be in the class)
    """
    if sort_order not in ["latest", "oldest"]:
        raise BadRequestException("sort_order must be 'latest' or 'oldest'")
    
    # Get notes filtered by class_id
    notes = await notes_service.get_notes_by_user_class(
        class_id=class_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    
    return NotesListResponse(
        notes=[NotesResponse.model_validate(n) for n in notes],
        total=len(notes),
        class_id=class_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
    )

