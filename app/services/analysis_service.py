"""Analysis/Bookmark service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from app.models.analysis import BookMarkedQuestion


class AnalysisService:
    """Service for bookmark and analysis operations - stateless, accepts db as method parameter"""

    async def create_bookmark(
        self,
        db: AsyncSession,
        user_id: UUID,
        question_id: UUID,
    ) -> BookMarkedQuestion:
        """Create a new bookmark for a question"""
        bookmark = BookMarkedQuestion(
            user_id=user_id,
            question_id=question_id,
        )
        db.add(bookmark)
        await db.commit()
        await db.refresh(bookmark)
        return bookmark

    async def get_bookmark_by_id(self, db: AsyncSession, bookmark_id: UUID) -> Optional[BookMarkedQuestion]:
        """Get a bookmark by ID"""
        result = await db.execute(
            select(BookMarkedQuestion).where(BookMarkedQuestion.id == bookmark_id)
        )
        return result.scalar_one_or_none()

    async def get_user_bookmarks(self, db: AsyncSession, user_id: UUID) -> List[BookMarkedQuestion]:
        """Get all bookmarks for a user"""
        result = await db.execute(
            select(BookMarkedQuestion)
            .where(BookMarkedQuestion.user_id == user_id)
            .order_by(BookMarkedQuestion.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_bookmark_by_user_and_question(
        self,
        db: AsyncSession,
        user_id: UUID,
        question_id: UUID,
    ) -> Optional[BookMarkedQuestion]:
        """Check if a user has bookmarked a specific question"""
        result = await db.execute(
            select(BookMarkedQuestion).where(
                BookMarkedQuestion.user_id == user_id,
                BookMarkedQuestion.question_id == question_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_bookmark(self, db: AsyncSession, bookmark_id: UUID) -> bool:
        """Delete a bookmark by ID"""
        bookmark = await self.get_bookmark_by_id(db, bookmark_id)
        if not bookmark:
            return False
        
        stmt = delete(BookMarkedQuestion).where(BookMarkedQuestion.id == bookmark_id)
        await db.execute(stmt)
        await db.commit()
        return True

    async def delete_bookmark_by_user_and_question(
        self,
        db: AsyncSession,
        user_id: UUID,
        question_id: UUID,
    ) -> bool:
        """Delete a bookmark by user and question ID (toggle off)"""
        bookmark = await self.get_bookmark_by_user_and_question(db, user_id, question_id)
        if not bookmark:
            return False
        
        stmt = delete(BookMarkedQuestion).where(
            BookMarkedQuestion.user_id == user_id,
            BookMarkedQuestion.question_id == question_id,
        )
        await db.execute(stmt)
        await db.commit()
        return True

    async def toggle_bookmark(
        self,
        db: AsyncSession,
        user_id: UUID,
        question_id: UUID,
    ) -> tuple[bool, Optional[BookMarkedQuestion]]:
        """
        Toggle bookmark status for a question.
        Returns (is_bookmarked, bookmark_object)
        """
        existing = await self.get_bookmark_by_user_and_question(db, user_id, question_id)
        
        if existing:
            await self.delete_bookmark(db, existing.id)
            return False, None
        else:
            bookmark = await self.create_bookmark(db, user_id, question_id)
            return True, bookmark

    async def is_bookmarked(self, db: AsyncSession, user_id: UUID, question_id: UUID) -> bool:
        """Check if a question is bookmarked by a user"""
        bookmark = await self.get_bookmark_by_user_and_question(db, user_id, question_id)
        return bookmark is not None
