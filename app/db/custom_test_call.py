"""Custom Test database calls"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from app.models.custom_test import CustomTest, CustomTestAnalysis, AttemptStatus
from app.models.linking import CustomTestQuestion
from app.models.Basequestion import Question


# ==================== Custom Test CRUD ====================

async def create_custom_test(
    db: AsyncSession,
    user_id: UUID,
    question_ids: List[UUID],
    status: AttemptStatus = AttemptStatus.not_started,
    time_assigned: int = 0
) -> CustomTest:
    """Create a new custom test with questions"""
    # Create the test
    test = CustomTest(
        user_id=user_id,
        status=status,
        time_assigned=time_assigned,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(test)
    await db.flush()  # Get the test ID
    
    # Add questions to the test
    for question_id in question_ids:
        test_question = CustomTestQuestion(
            test_id=test.id,
            question_id=question_id,
        )
        db.add(test_question)
    
    await db.commit()
    await db.refresh(test)
    return test


async def get_custom_test_by_id(
    db: AsyncSession,
    test_id: UUID,
) -> Optional[CustomTest]:
    """Get a custom test by ID"""
    result = await db.execute(
        select(CustomTest).where(CustomTest.id == test_id)
    )
    return result.scalar_one_or_none()


async def get_custom_test_with_questions(
    db: AsyncSession,
    test_id: UUID,
) -> Optional[CustomTest]:
    """Get a custom test with its questions"""
    result = await db.execute(
        select(CustomTest)
        .where(CustomTest.id == test_id)
        .options(
            selectinload(CustomTest.questions)
            .selectinload(CustomTestQuestion.question)
        )
    )
    return result.scalar_one_or_none()


async def get_user_custom_tests(
    db: AsyncSession,
    user_id: UUID,
    status: Optional[AttemptStatus] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[List[CustomTest], int]:
    """Get all custom tests for a user with pagination"""
    # Base query
    query = select(CustomTest).where(CustomTest.user_id == user_id)
    count_query = select(func.count(CustomTest.id)).where(CustomTest.user_id == user_id)
    
    # Apply status filter if provided
    if status:
        query = query.where(CustomTest.status == status)
        count_query = count_query.where(CustomTest.status == status)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(CustomTest.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def update_custom_test_status(
    db: AsyncSession,
    test_id: UUID,
    status: AttemptStatus,
) -> Optional[CustomTest]:
    """Update the status of a custom test"""
    test = await get_custom_test_by_id(db, test_id)
    if not test:
        return None
    
    test.status = status
    test.updated_at = datetime.now()
    
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test


async def delete_custom_test(
    db: AsyncSession,
    test_id: UUID,
) -> bool:
    """Delete a custom test and its linked questions"""
    # First delete linked questions
    await db.execute(
        delete(CustomTestQuestion).where(CustomTestQuestion.test_id == test_id)
    )
    
    # Then delete the test
    result = await db.execute(
        delete(CustomTest).where(CustomTest.id == test_id)
    )
    await db.commit()
    
    return result.rowcount > 0



async def get_test_questions(
    db: AsyncSession,
    test_id: UUID,
) -> List[Question]:
    """Get all questions for a test"""
    result = await db.execute(
        select(Question)
        .join(CustomTestQuestion, CustomTestQuestion.question_id == Question.id)
        .where(CustomTestQuestion.test_id == test_id)
    )
    return list(result.scalars().all())


# ==================== Custom Test Analysis CRUD ====================

async def create_custom_test_analysis(
    db: AsyncSession,
    user_id: UUID,
    custom_test_id: UUID,
    marks_obtained: int,
    total_marks: int,
    total_time_spent: int,
    correct: int,
    incorrect: int,
    unattempted: int,
) -> CustomTestAnalysis:
    """Create a new custom test analysis"""
    analysis = CustomTestAnalysis(
        user_id=user_id,
        marks_obtained=marks_obtained,
        total_marks=total_marks,
        total_time_spent=total_time_spent,
        correct=correct,
        incorrect=incorrect,
        custom_test_id=custom_test_id,
        unattempted=unattempted,
        submitted_at=datetime.now(),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def get_analysis_by_id(
    db: AsyncSession,
    analysis_id: UUID,
) -> Optional[CustomTestAnalysis]:
    """Get a custom test analysis by ID"""
    result = await db.execute(
        select(CustomTestAnalysis).where(CustomTestAnalysis.id == analysis_id)
    )
    return result.scalar_one_or_none()


async def get_user_analyses(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20,
) -> tuple[List[CustomTestAnalysis], int]:
    """Get all analyses for a user with pagination"""
    # Count query
    count_result = await db.execute(
        select(func.count(CustomTestAnalysis.id))
        .where(CustomTestAnalysis.user_id == user_id)
    )
    total = count_result.scalar() or 0
    
    # Data query
    result = await db.execute(
        select(CustomTestAnalysis)
        .where(CustomTestAnalysis.user_id == user_id)
        .order_by(CustomTestAnalysis.submitted_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def delete_analysis(
    db: AsyncSession,
    analysis_id: UUID,
) -> bool:
    """Delete a custom test analysis"""
    result = await db.execute(
        delete(CustomTestAnalysis).where(CustomTestAnalysis.id == analysis_id)
    )
    await db.commit()
    return result.rowcount > 0


# ==================== Custom Test Statistics ====================

async def get_user_test_stats(
    db: AsyncSession,
    user_id: UUID,
) -> dict:
    """Get custom test statistics for a user"""
    # Total tests
    total_result = await db.execute(
        select(func.count(CustomTest.id))
        .where(CustomTest.user_id == user_id)
    )
    total_tests = total_result.scalar() or 0
    
    # Tests by status
    completed_result = await db.execute(
        select(func.count(CustomTest.id))
        .where(
            CustomTest.user_id == user_id,
            CustomTest.status == AttemptStatus.finished,
        )
    )
    completed = completed_result.scalar() or 0
    
    active_result = await db.execute(
        select(func.count(CustomTest.id))
        .where(
            CustomTest.user_id == user_id,
            CustomTest.status == AttemptStatus.active,
        )
    )
    active = active_result.scalar() or 0
    
    not_started_result = await db.execute(
        select(func.count(CustomTest.id))
        .where(
            CustomTest.user_id == user_id,
            CustomTest.status == AttemptStatus.not_started,
        )
    )
    not_started = not_started_result.scalar() or 0
    
    # Analysis aggregates
    analysis_result = await db.execute(
        select(
            func.coalesce(func.sum(CustomTestAnalysis.correct), 0),
            func.coalesce(func.sum(CustomTestAnalysis.incorrect), 0),
            func.coalesce(func.sum(CustomTestAnalysis.unattempted), 0),
            func.coalesce(func.sum(CustomTestAnalysis.total_time_spent), 0),
            func.coalesce(func.sum(CustomTestAnalysis.marks_obtained), 0),
            func.coalesce(func.sum(CustomTestAnalysis.total_marks), 0),
        )
        .where(CustomTestAnalysis.user_id == user_id)
    )
    stats = analysis_result.one()
    
    total_correct = stats[0]
    total_incorrect = stats[1]
    total_unattempted = stats[2]
    total_time = stats[3]
    total_marks_obtained = stats[4]
    total_marks_possible = stats[5]
    
    total_attempted = total_correct + total_incorrect + total_unattempted
    
    return {
        "total_tests": total_tests,
        "tests_completed": completed,
        "tests_in_progress": active,
        "tests_not_started": not_started,
        "total_questions_attempted": total_correct + total_incorrect,
        "total_correct": total_correct,
        "total_incorrect": total_incorrect,
        "total_unattempted": total_unattempted,
        "overall_accuracy": round((total_correct / (total_correct + total_incorrect) * 100) if (total_correct + total_incorrect) > 0 else 0, 2),
        "total_time_spent": total_time,
        "average_score_percentage": round((total_marks_obtained / total_marks_possible * 100) if total_marks_possible > 0 else 0, 2),
    }

