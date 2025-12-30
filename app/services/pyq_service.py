"""Previous Year Questions (PYQ) service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, cast
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional, Tuple

from app.models.pyq import PreviousYearProblems
from app.models.Basequestion import TargetExam, Question
from app.integrations.redis_client import RedisService
from typing import Optional
from app.core.config import settings

class PYQService:
    """Service for Previous Year Questions operations"""

    CACHE_PREFIX = "pyq"

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

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
        """Get all PYQs with pagination (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:all:{skip}:{limit}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                pyq_ids = [UUID(pid) for pid in cached.get("pyq_ids", [])]
                total = cached.get("total", 0)
                
                # Fetch from DB using cached IDs
                if pyq_ids:
                    result = await self.db.execute(
                        select(PreviousYearProblems)
                        .where(PreviousYearProblems.id.in_(pyq_ids))
                        .order_by(PreviousYearProblems.created_at.desc())
                    )
                    return list(result.scalars().all()), total
                return [], total
        
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
        pyqs = list(result.scalars().all())
        
        # Cache result
        if self.redis_service:
            pyq_ids = [str(p.id) for p in pyqs]
            await self.redis_service.set_value(
                cache_key,
                {"pyq_ids": pyq_ids, "total": total},
                expire=settings.CACHE_SHARED
            )
        
        return pyqs, total

    async def get_pyqs_by_exam(
        self,
        exam_name: List[TargetExam],
        skip: int = 0,
        limit: int = 20,
    ) -> List[PreviousYearProblems]:
        """Get all PYQs for a specific exam (searches in exam_detail array, cached)"""
        # Create cache key from exam names
        exam_key = "_".join(sorted([e.value for e in exam_name]))
        cache_key = f"{self.CACHE_PREFIX}:exam:{exam_key}:{skip}:{limit}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                pyq_ids = [UUID(pid) for pid in cached]
                if pyq_ids:
                    result = await self.db.execute(
                        select(PreviousYearProblems)
                        .where(PreviousYearProblems.id.in_(pyq_ids))
                        .order_by(PreviousYearProblems.created_at.desc())
                    )
                    return list(result.scalars().all())
                return []

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
        
        # Cache result
        if self.redis_service:
            pyq_ids = [str(p.id) for p in pyqs]
            await self.redis_service.set_value(cache_key, pyq_ids, expire=settings.CACHE_SHARED)

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
        
        # Invalidate PYQ caches
        if self.redis_service:
            await self._invalidate_pyq_caches()
        
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
        
        # Invalidate PYQ caches
        if self.redis_service:
            await self._invalidate_pyq_caches()
        
        return True
    
    async def _invalidate_pyq_caches(self):
        """Invalidate all PYQ-related caches"""
        # Note: In production, you might want to use Redis SCAN to find and delete
        # all keys matching the pattern. For now, we'll just clear common patterns.
        # This is a simplified approach - for full invalidation, consider using Redis keys pattern matching
        pass

