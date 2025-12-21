"""Class endpoints"""

from typing import List
from uuid import UUID
from fastapi import APIRouter

from app.api.v1.dependencies import ClassServiceDep
from app.schemas.question import (
    ClassCreateRequest,
    ClassResponse,
    ClassListResponse,
    ClassWithSubjectsResponse,
)
from app.exceptions.http_exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/class", tags=["Classes"])


@router.post("/", response_model=ClassResponse, status_code=201)
async def create_class(
    class_service: ClassServiceDep,
    request: ClassCreateRequest,
) -> ClassResponse:
    """Create a new class"""
    try:
        print(request.name)
        new_class = await class_service.create_class(request.name)
        return ClassResponse.model_validate(new_class)
    except Exception as e:
        raise BadRequestException(f"Failed to create class: {str(e)}")


@router.get("/", response_model=ClassListResponse)
async def get_all_classes(
    class_service: ClassServiceDep,
) -> ClassListResponse:
    """Get all classes"""
    classes = await class_service.get_all_classes()
    return ClassListResponse(
        classes=[ClassResponse.model_validate(c) for c in classes],
        total=len(classes)
    )


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(
    class_service: ClassServiceDep,
    class_id: UUID,
) -> ClassResponse:
    """Get a class by ID"""
    result = await class_service.get_class_by_id(class_id)
    if not result:
        raise NotFoundException(f"Class with ID {class_id} not found")
    return ClassResponse.model_validate(result)


@router.get("/{class_id}/subjects", response_model=ClassWithSubjectsResponse)
async def get_class_with_subjects(
    class_service: ClassServiceDep,
    class_id: UUID,
) -> ClassWithSubjectsResponse:
    """Get a class with all its subjects, chapters, and questions"""
    result = await class_service.get_class_with_subjects(class_id)
    if not result:
        raise NotFoundException(f"Class with ID {class_id} not found")
    return ClassWithSubjectsResponse.model_validate(result)


@router.delete("/{class_id}", status_code=204)
async def delete_class(
    class_service: ClassServiceDep,
    class_id: UUID,
) -> None:
    """Delete a class by ID"""
    deleted = await class_service.delete_class(class_id)
    if not deleted:
        raise NotFoundException(f"Class with ID {class_id} not found")
