"""Subject endpoints"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Query

from app.api.v1.dependencies import SubjectServiceDep
from app.schemas.question import (
    SubjectCreateRequest,
    SubjectResponse,
    SubjectListResponse,
    SubjectWithChaptersResponse,
)
from app.exceptions.http_exceptions import NotFoundException, BadRequestException
from app.models.user import TargetExam

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.post("/", response_model=SubjectResponse, status_code=201)
async def create_subject(
    subject_service: SubjectServiceDep,
    request: SubjectCreateRequest,
) -> SubjectResponse:
    """Create a new subject"""
    try:
        new_subject = await subject_service.create_subject(
            request.subject_type, 
            request.class_id,
            request.exam_type
        )
        return SubjectResponse.model_validate(new_subject)
    except Exception as e:
        raise BadRequestException(f"Failed to create subject: {str(e)}")


@router.get("/", response_model=SubjectListResponse)
async def get_all_subjects(
    subject_service: SubjectServiceDep,
    class_id: Optional[UUID] = Query(None, description="Filter subjects by class ID"),
    exam_type: Optional[TargetExam] = Query(None, description="Filter subjects by exam type"),
) -> SubjectListResponse:
    """Get all subjects, optionally filtered by class ID or exam type"""
    if exam_type:
        subjects = await subject_service.get_subjects_by_exam_type(exam_type)
        # Further filter by class_id if provided
        if class_id:
            subjects = [s for s in subjects if s.class_id == class_id]
    elif class_id:
        subjects = await subject_service.get_subjects_by_class(class_id)
    else:
        subjects = await subject_service.get_all_subjects()
    
    return SubjectListResponse(
        subjects=[SubjectResponse.model_validate(s) for s in subjects],
        total=len(subjects)
    )


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_service: SubjectServiceDep,
    subject_id: UUID,
) -> SubjectResponse:
    """Get a subject by ID"""
    result = await subject_service.get_subject_by_id(subject_id)
    if not result:
        raise NotFoundException(f"Subject with ID {subject_id} not found")
    return SubjectResponse.model_validate(result)


@router.get("/{subject_id}/chapters", response_model=SubjectWithChaptersResponse)
async def get_subject_with_chapters(
    subject_service: SubjectServiceDep,
    subject_id: UUID,
) -> SubjectWithChaptersResponse:
    """Get a subject with all its chapters and questions"""
    result = await subject_service.get_subject_with_chapters(subject_id)
    if not result:
        raise NotFoundException(f"Subject with ID {subject_id} not found")
    return SubjectWithChaptersResponse.model_validate(result)


@router.delete("/{subject_id}", status_code=204)
async def delete_subject(
    subject_service: SubjectServiceDep,
    subject_id: UUID,
) -> None:
    """Delete a subject by ID"""
    deleted = await subject_service.delete_subject(subject_id)
    if not deleted:
        raise NotFoundException(f"Subject with ID {subject_id} not found")

