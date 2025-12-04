"""Previous Year Questions (PYQ) endpoints"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Query

from app.api.v1.dependencies import PYQServiceDep, CurrentUser
from app.schemas.question import (
    PYQCreateRequest,
    PYQResponse,
    PYQUpdateRequest,
    PYQListResponse,
)
from app.exceptions.http_exceptions import NotFoundException, BadRequestException, ConflictException

router = APIRouter(prefix="/pyq", tags=["Previous Year Questions"])


@router.post("/", response_model=PYQResponse, status_code=201)
async def create_pyq(
    pyq_service: PYQServiceDep,
    current_user: CurrentUser,
    request: PYQCreateRequest,
) -> PYQResponse:
    """Create a new PYQ entry"""
    # Check if PYQ already exists for this question
    existing = await pyq_service.get_pyq_by_question(request.question_id)
    if existing:
        raise ConflictException("PYQ entry already exists for this question")
    
    try:
        pyq = await pyq_service.create_pyq(
            user_id=current_user.id,
            question_id=request.question_id,
            exam_detail=request.exam_detail,
        )
        return PYQResponse(
            id=pyq.id,
            user_id=pyq.user_id,
            question_id=pyq.question_id,
            exam_detail=pyq.exam_detail,
            created_at=str(pyq.created_at),
        )
    except Exception as e:
        raise BadRequestException(f"Failed to create PYQ: {str(e)}")


@router.get("/", response_model=PYQListResponse)
async def get_all_pyqs(
    pyq_service: PYQServiceDep,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
    exam: Optional[str] = Query(None, description="Filter by exam name"),
) -> PYQListResponse:
    """Get all PYQs with pagination and optional exam filter"""
    if exam:
        pyqs, total = await pyq_service.get_pyqs_by_exam(
            exam_name=exam,
            skip=skip,
            limit=limit,
        )
    else:
        pyqs, total = await pyq_service.get_all_pyqs(skip=skip, limit=limit)
    
    return PYQListResponse(
        pyqs=[
            PYQResponse(
                id=p.id,
                user_id=p.user_id,
                question_id=p.question_id,
                exam_detail=p.exam_detail,
                created_at=str(p.created_at),
            )
            for p in pyqs
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/my", response_model=PYQListResponse)
async def get_my_pyqs(
    pyq_service: PYQServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> PYQListResponse:
    """Get all PYQs created by the current user"""
    pyqs, total = await pyq_service.get_pyqs_by_user(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return PYQListResponse(
        pyqs=[
            PYQResponse(
                id=p.id,
                user_id=p.user_id,
                question_id=p.question_id,
                exam_detail=p.exam_detail,
                created_at=str(p.created_at),
            )
            for p in pyqs
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{pyq_id}", response_model=PYQResponse)
async def get_pyq(
    pyq_service: PYQServiceDep,
    pyq_id: UUID,
) -> PYQResponse:
    """Get a specific PYQ by ID"""
    pyq = await pyq_service.get_pyq_by_id(pyq_id)
    if not pyq:
        raise NotFoundException(f"PYQ with ID {pyq_id} not found")
    
    return PYQResponse(
        id=pyq.id,
        user_id=pyq.user_id,
        question_id=pyq.question_id,
        exam_detail=pyq.exam_detail,
        created_at=str(pyq.created_at),
    )


@router.get("/question/{question_id}", response_model=PYQResponse)
async def get_pyq_by_question(
    pyq_service: PYQServiceDep,
    question_id: UUID,
) -> PYQResponse:
    """Get PYQ entry for a specific question"""
    pyq = await pyq_service.get_pyq_by_question(question_id)
    if not pyq:
        raise NotFoundException(f"PYQ for question {question_id} not found")
    
    return PYQResponse(
        id=pyq.id,
        user_id=pyq.user_id,
        question_id=pyq.question_id,
        exam_detail=pyq.exam_detail,
        created_at=str(pyq.created_at),
    )


@router.put("/{pyq_id}", response_model=PYQResponse)
async def update_pyq(
    pyq_service: PYQServiceDep,
    current_user: CurrentUser,
    pyq_id: UUID,
    request: PYQUpdateRequest,
) -> PYQResponse:
    """Update a PYQ entry"""
    # Check if PYQ exists
    existing = await pyq_service.get_pyq_by_id(pyq_id)
    if not existing:
        raise NotFoundException(f"PYQ with ID {pyq_id} not found")
    
    # Ensure user owns this PYQ
    if existing.user_id != current_user.id:
        raise NotFoundException(f"PYQ with ID {pyq_id} not found")
    
    pyq = await pyq_service.update_pyq(
        pyq_id=pyq_id,
        exam_detail=request.exam_detail,
    )
    
    if not pyq:
        raise NotFoundException(f"PYQ with ID {pyq_id} not found")
    
    return PYQResponse(
        id=pyq.id,
        user_id=pyq.user_id,
        question_id=pyq.question_id,
        exam_detail=pyq.exam_detail,
        created_at=str(pyq.created_at),
    )


@router.delete("/{pyq_id}", status_code=204)
async def delete_pyq(
    pyq_service: PYQServiceDep,
    current_user: CurrentUser,
    pyq_id: UUID,
) -> None:
    """Delete a PYQ by ID"""
    # Check if PYQ exists
    existing = await pyq_service.get_pyq_by_id(pyq_id)
    if not existing:
        raise NotFoundException(f"PYQ with ID {pyq_id} not found")
    
    # Ensure user owns this PYQ
    if existing.user_id != current_user.id:
        raise NotFoundException(f"PYQ with ID {pyq_id} not found")
    
    deleted = await pyq_service.delete_pyq(pyq_id)
    if not deleted:
        raise NotFoundException(f"PYQ with ID {pyq_id} not found")


@router.delete("/question/{question_id}", status_code=204)
async def delete_pyq_by_question(
    pyq_service: PYQServiceDep,
    current_user: CurrentUser,
    question_id: UUID,
) -> None:
    """Delete PYQ entry for a specific question"""
    # Check if PYQ exists and belongs to user
    existing = await pyq_service.get_pyq_by_question(question_id)
    if not existing:
        raise NotFoundException(f"PYQ for question {question_id} not found")
    
    if existing.user_id != current_user.id:
        raise NotFoundException(f"PYQ for question {question_id} not found")
    
    deleted = await pyq_service.delete_pyq_by_question(question_id)
    if not deleted:
        raise NotFoundException(f"PYQ for question {question_id} not found")

