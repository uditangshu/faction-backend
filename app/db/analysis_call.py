from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import BookMarkedQuestion
from sqlalchemy import delete

async def create_bookmark(
        db:AsyncSession,
        question_id:UUID,
) -> BookMarkedQuestion:
    
    bm_ques= BookMarkedQuestion(
        question_id
    )
    db.add(bm_ques)
    await db.commit()
    await db.refresh(bm_ques)

    return bm_ques

async def delete_bookmark(
        db:AsyncSession,
        bm_id: UUID
) :
    stmt= delete(BookMarkedQuestion).where(BookMarkedQuestion.id == bm_id)
    await db.execute(stmt)
