"""Contest service"""

from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List, Tuple

from app.models.contest import Contest, ContestStatus
from app.models.linking import ContestQuestions
from app.models.Basequestion import Question


class ContestService:
    """Service for contest operations - stateless, accepts db as method parameter"""

    async def create_contest(
        self,
        db: AsyncSession,
        total_time: int,
        status: ContestStatus,
        starts_at: datetime,
        ends_at: datetime,
        question_ids: List[UUID],
    ) -> Contest:
        """Create a new contest"""
        contest = Contest(
            total_time=total_time,
            status=status,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        db.add(contest)
        await db.commit()
        await db.refresh(contest)
        
        # Create ContestQuestions entries to link questions to the contest
        for question_id in question_ids:
            contest_question = ContestQuestions(
                contest_id=contest.id,
                question_id=question_id,
            )
            db.add(contest_question)
        
        await db.commit()
        return contest

    async def get_contest_by_id(self, db: AsyncSession, contest_id: UUID) -> Optional[Contest]:
        """Get contest by ID"""
        result = await db.execute(
            select(Contest).where(Contest.id == contest_id)
        )
        return result.scalar_one_or_none()

    async def update_contest(
        self,
        db: AsyncSession,
        contest_id: UUID,
        total_time: Optional[int] = None,
        status: Optional[ContestStatus] = None,
        starts_at: Optional[datetime] = None,
        ends_at: Optional[datetime] = None,
    ) -> Optional[Contest]:
        """Update an existing contest"""
        contest = await self.get_contest_by_id(db, contest_id)
        if not contest:
            return None

        if total_time is not None:
            contest.total_time = total_time
        if status is not None:
            contest.status = status
        if starts_at is not None:
            contest.starts_at = starts_at
        if ends_at is not None:
            contest.ends_at = ends_at

        db.add(contest)
        await db.commit()
        await db.refresh(contest)
        return contest

    async def delete_contest(self, db: AsyncSession, contest_id: UUID) -> bool:
        """Delete a contest by ID"""
        contest = await self.get_contest_by_id(db, contest_id)
        if not contest:
            return False
        
        stmt = delete(Contest).where(Contest.id == contest_id)
        await db.execute(stmt)
        await db.commit()
        return True

    async def get_contest_with_questions(self, db: AsyncSession, contest_id: UUID) -> Optional[Tuple[Contest, List[Question]]]:
        """Get contest by ID with all linked questions"""
        # Get the contest
        contest = await self.get_contest_by_id(db, contest_id)
        if not contest:
            return None
        
        # Get all questions linked to this contest
        result = await db.execute(
            select(Question)
            .join(ContestQuestions, ContestQuestions.question_id == Question.id)
            .where(ContestQuestions.contest_id == contest_id)
        )
        questions = list(result.scalars().all())
        
        return contest, questions
