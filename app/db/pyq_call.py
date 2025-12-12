from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.models.pyq import PreviousYearProblems

async def create_pyq(db: AsyncSession,
                     question_id: UUID,
                     year: int,
                     exam_detail: List[str]                   
 )->PreviousYearProblems:

    pyq= PreviousYearProblems(
        question_id=question_id,
        year=year,
        exam_detail=exam_detail,
    )
    db.add(pyq)
    await db.commit()
    await db.refresh(pyq)
    return pyq
    
    
async def update_pyq(db: AsyncSession,updated_pyq: PreviousYearProblems
                     )->PreviousYearProblems:
    db.merge(updated_pyq)
    await db.commit()
    await db.refresh(updated_pyq)
    return updated_pyq
    

async def delete_pyq(db: AsyncSession, id: UUID):
    stmt = delete(PreviousYearProblems).where(PreviousYearProblems.id==id)
    await db.execute(stmt)
    