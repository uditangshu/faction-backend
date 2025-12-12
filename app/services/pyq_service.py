"""Previous Year Questions (PYQ) service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, cast
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional, Tuple

from app.models.pyq import PreviousYearProblems
from app.models.Basequestion import TargetExam, Question

class PYQService:
    """Service for Previous Year Questions operations - stateless, accepts db as method parameter"""

    async def create_pyq(
        self,
        db: AsyncSession,
        question_id: UUID,
        exam_detail: List[str],
    ) -> PreviousYearProblems:
        """Create a new PYQ entry"""
        pyq = PreviousYearProblems(
            question_id=question_id,
            exam_detail=exam_detail,
        )
        db.add(pyq)
        await db.commit()
        await db.refresh(pyq)
        return pyq

    async def get_pyq_by_id(self, db: AsyncSession, pyq_id: UUID) -> Optional[PreviousYearProblems]:
        """Get a PYQ by ID"""
        result = await db.execute(
            select(PreviousYearProblems).where(PreviousYearProblems.id == pyq_id)
        )
        return result.scalar_one_or_none()

    async def get_pyq_by_question(self, db: AsyncSession, question_id: UUID) -> Optional[PreviousYearProblems]:
        """Get PYQ entry for a specific question"""
        result = await db.execute(
            select(PreviousYearProblems)
            .where(PreviousYearProblems.question_id == question_id)
        )
        return result.scalar_one_or_none()

    async def get_all_pyqs(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[PreviousYearProblems], int]:
        """Get all PYQs with pagination"""
        # Count query
        count_result = await db.execute(
            select(func.count(PreviousYearProblems.id))
        )
        total = count_result.scalar() or 0

        # Data query
        result = await db.execute(
            select(PreviousYearProblems)
            .order_by(PreviousYearProblems.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_pyqs_by_exam(
        self,
        db: AsyncSession,
        exam_name: List[TargetExam],
        skip: int = 0,
        limit: int = 20,
    ) -> List[PreviousYearProblems]:
        """Get all PYQs for a specific exam (searches in exam_detail array)"""
        # This searches for exam_name within the JSON array
        result = await db.execute(
            select(PreviousYearProblems, Question)
            .join(Question, PreviousYearProblems.question_id == Question.id)
            .filter(cast(Question.exam_type, JSONB).contains([exam_name]))
            .order_by(PreviousYearProblems.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        pyqs = []
        
        for pyq, question in result:
            pyqs.append(pyq)

        return list(pyqs)
    
    async def update_pyq(
        self,
        db: AsyncSession,
        pyq_id: UUID,
        exam_detail: Optional[List[str]] = None,
    ) -> Optional[PreviousYearProblems]:
        """Update a PYQ entry"""
        pyq = await self.get_pyq_by_id(db, pyq_id)
        if not pyq:
            return None

        if exam_detail is not None:
            pyq.exam_detail = exam_detail

        db.add(pyq)
        await db.commit()
        await db.refresh(pyq)
        return pyq

    async def delete_pyq(self, db: AsyncSession, pyq_id: UUID) -> bool:
        """Delete a PYQ by ID"""
        pyq = await self.get_pyq_by_id(db, pyq_id)
        if not pyq:
            return False

        stmt = delete(PreviousYearProblems).where(PreviousYearProblems.id == pyq_id)
        await db.execute(stmt)
        await db.commit()
        return True

    async def delete_pyq_by_question(self, db: AsyncSession, question_id: UUID) -> bool:
        """Delete PYQ entry for a specific question"""
        pyq = await self.get_pyq_by_question(db, question_id)
        if not pyq:
            return False

        stmt = delete(PreviousYearProblems).where(
            PreviousYearProblems.question_id == question_id
        )
        await db.execute(stmt)
        await db.commit()
        return True
