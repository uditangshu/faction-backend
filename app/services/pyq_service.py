"""Previous Year Questions (PYQ) service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, cast
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional, Tuple

from app.models.pyq import PreviousYearProblems
from app.models.Basequestion import TargetExam, Question

class PYQService:
    """Service for Previous Year Questions operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_pyq(
        self,
        question_id: UUID,
        year: int,
        exam_detail: List[str],
    ) -> PreviousYearProblems:
        """Create a new PYQ entry"""
        pyq = PreviousYearProblems(
            question_id=question_id,
            year=year,
            exam_detail=exam_detail,
        )
        self.db.add(pyq)
        await self.db.commit()
        await self.db.refresh(pyq)
        return pyq

    async def get_pyq_by_id(self, pyq_id: UUID) -> Optional[PreviousYearProblems]:
        """Get a PYQ by ID"""
        result = await self.db.execute(
            select(PreviousYearProblems).where(PreviousYearProblems.id == pyq_id)
        )
        return result.scalar_one_or_none()

    async def get_pyq_by_question(self, question_id: UUID) -> Optional[PreviousYearProblems]:
        """Get PYQ entry for a specific question"""
        result = await self.db.execute(
            select(PreviousYearProblems)
            .where(PreviousYearProblems.question_id == question_id)
        )
        return result.scalar_one_or_none()

    async def get_all_pyqs(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[PreviousYearProblems], int]:
        """Get all PYQs with pagination"""
        # Count query
        count_result = await self.db.execute(
            select(func.count(PreviousYearProblems.id))
        )
        total = count_result.scalar() or 0

        # Data query
        result = await self.db.execute(
            select(PreviousYearProblems)
            .order_by(PreviousYearProblems.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_pyqs_by_exam(
        self,
        exam_name: List[TargetExam],
        skip: int = 0,
        limit: int = 20,
    ) -> List[PreviousYearProblems]:
        """Get all PYQs for a specific exam (searches in exam_detail array)"""
        # This searches for exam_name within the JSON array
        # Count query

        # Data query
        result = await self.db.execute(
            select(PreviousYearProblems,Question)
            .join(Question, PreviousYearProblems.question_id==Question.id)
            .filter(cast(Question.exam_type, JSONB).contains([exam_name]))
            .order_by(PreviousYearProblems.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        pyqs=[]
        
        for pyq, question in result:
            print("this is the service printing up", pyq)
            pyqs.append(pyq)

        return list(pyqs)
    
    async def update_pyq(
        self,
        pyq_id: UUID,
        year: Optional[int] = None,
        exam_detail: Optional[List[str]] = None,
    ) -> Optional[PreviousYearProblems]:
        """Update a PYQ entry"""
        pyq = await self.get_pyq_by_id(pyq_id)
        if not pyq:
            return None

        if year is not None:
            pyq.year = year
        if exam_detail is not None:
            pyq.exam_detail = exam_detail

        self.db.add(pyq)
        await self.db.commit()
        await self.db.refresh(pyq)
        return pyq

    async def delete_pyq(self, pyq_id: UUID) -> bool:
        """Delete a PYQ by ID"""
        pyq = await self.get_pyq_by_id(pyq_id)
        if not pyq:
            return False

        stmt = delete(PreviousYearProblems).where(PreviousYearProblems.id == pyq_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def delete_pyq_by_question(self, question_id: UUID) -> bool:
        """Delete PYQ entry for a specific question"""
        pyq = await self.get_pyq_by_question(question_id)
        if not pyq:
            return False

        stmt = delete(PreviousYearProblems).where(
            PreviousYearProblems.question_id == question_id
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return True

