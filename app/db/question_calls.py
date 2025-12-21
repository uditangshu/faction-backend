"""Question database calls"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, join
from sqlalchemy.orm import selectinload

from app.models.Basequestion import (
Question, Class, Subject_Type,
Subject, Chapter, Topic, QuestionType, DifficultyLevel
)
from app.models.user import TargetExam


async def create_class(db : AsyncSession, name : str) -> Class:
    """Create a new class"""
    classes = Class(name=name)
    print(classes)
    db.add(classes)
    await db.commit()
    await db.refresh(classes)
    return classes

#have to think what to return***
async def delete_class(db : AsyncSession, class_id: UUID):
    """Delete the classes"""
    stmt= delete(Class).where(Class.id == class_id)
    await db.execute(stmt)
    

async def update_class(db : AsyncSession, updated_class: Class):
    """Update the classes"""
    db.merge(updated_class)
    await db.commit()
    await db.refresh(Class)
    return updated_class


#subjects
async def create_subject(db : AsyncSession, subject_type: Subject_Type, class_id : UUID, exam_type: Optional[List[TargetExam]] = None) -> Subject:
    """Create a new subject"""
    new_subject = Subject(
        subject_type=subject_type, 
        class_id=class_id,
        exam_type=exam_type if exam_type is not None else []
    )
    
    db.add(new_subject)
    await db.commit()
    await db.refresh(new_subject)
    return new_subject


#have to think what to return***
async def delete_subject(db : AsyncSession, subject_id: UUID):
    """Delete the classes"""
    stmt= delete(Subject).where(Subject.id == subject_id)
    await db.execute(stmt)
    

async def update_subject(db : AsyncSession, updated_subject: Subject):
    """Update the classes"""
    db.merge(updated_subject)
    await db.commit()
    await db.refresh(updated_subject)
    return updated_subject


#chapters
async def create_chaps(db : AsyncSession, sub_id : UUID, name: str) -> Chapter:
    """Create a new chapter"""
    chap = Chapter(
        name=name,
        subject_id=sub_id
    )
    db.add(chap)
    await db.commit()
    await db.refresh(chap)
    return chap

#have to think what to return***
async def delete_chaps(db : AsyncSession, chap_id: UUID):
    """Delete the classes"""
    stmt= delete(Chapter).where(Chapter.id == chap_id)
    await db.execute(stmt)
    

async def update_chaps(db : AsyncSession, updated_chap: Chapter):
    """Update the classes"""
    db.merge(updated_chap)
    await db.commit()
    await db.refresh(updated_chap)
    return updated_chap


#topics
async def create_topic(db: AsyncSession, chapter_id: UUID, name: str) -> Topic:
    """Create a new topic"""
    topic = Topic(
        name=name,
        chapter_id=chapter_id
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


async def delete_topic(db: AsyncSession, topic_id: UUID):
    """Delete a topic"""
    stmt = delete(Topic).where(Topic.id == topic_id)
    await db.execute(stmt)


async def update_topic(db: AsyncSession, updated_topic: Topic):
    """Update a topic"""
    db.merge(updated_topic)
    await db.commit()
    await db.refresh(updated_topic)
    return updated_topic


async def get_nested_topics(db: AsyncSession, topic_id: UUID) -> Optional[Topic]:
    """Get topic with questions"""
    result = await db.execute(
        select(Topic)
        .where(Topic.id == topic_id)
        .options(
            selectinload(Topic.questions)
        )
    )
    return result.scalar_one_or_none()


#question

async def create_question(db : AsyncSession,
                          chapter_id : UUID,
                          type : QuestionType,
                          difficulty : DifficultyLevel,
                          exam_type : List[TargetExam],
                          question_text : str,
                          marks : int,
                          solution_text : str,
                          question_image : Optional[str],
                          integer_answer : Optional[int],
                          mcq_options: Optional[List[str]],
                          mcq_correct_option: Optional[List[int]],
                          scq_options: Optional[List[str]],
                          scq_correct_options: Optional[int],
                          questions_solved: int
                         ) -> Class:
    """Create A New Question"""
    ques= Question(
    chapter_id,
    type,
    difficulty,
    exam_type,
    question_text,
    marks,
    solution_text,
    question_image,
    integer_answer,
    mcq_options,
    mcq_correct_option,
    scq_options,
    scq_correct_options,
    questions_solved,
    )
    
    db.add(ques)
    await db.commit()
    await db.refresh(ques)
    return ques

#have to think what to return***
async def delete_question(db : AsyncSession, ques_id: UUID):
    """Delete the Question"""
    stmt= delete(Question).where(Question.id == ques_id)
    await db.execute(stmt)


async def update_question(db : AsyncSession, updated_ques: Question):
    """Update the Question"""
    db.merge(updated_ques)
    await db.commit()
    await db.refresh(updated_ques)
    return updated_ques


async def get_nested_class(db: AsyncSession, class_id: UUID) -> Optional[Class]:
    """Get question by ID"""
    result = await db.execute(
        select(Class)
        .where(Class.id == class_id)
        .options(
            selectinload(Class.subjects)
        )
    )
    return result.scalar_one_or_none()


async def get_nested_subjects(db: AsyncSession, sub_id: UUID) -> Optional[Subject]:
    """Get subjects by ID"""
    result = await db.execute(
        select(Subject)
        .where(Subject.id == sub_id)
        .options(
            selectinload(Subject.chapters)
        )
    )
    return result.scalar_one_or_none()

async def get_nested_chapters(db: AsyncSession, chap_id: UUID) -> Optional[Chapter]:
    """Get Chapters with topics and questions"""
    result = await db.execute(
        select(Chapter)
        .where(Chapter.id == chap_id)
        .options(
            selectinload(Chapter.topics)
                .selectinload(Topic.questions)
        )
    )
    return result.scalar_one_or_none()

async def get_questions(db: AsyncSession, ques_id: UUID) -> Optional[Question]:
    """Get Question by ID"""
    result = await db.execute(
        select(Question)
        .where(Question.id == ques_id)
    )
    return result.scalar_one_or_none()


async def get(
    db: AsyncSession,
    subject_id: Optional[UUID] = None,
    class_id : Optional[UUID] = None,
    chap_id : Optional[UUID]= None,
    difficulty_level: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[Question]:
    """Get questions with filters"""
    query = select(Question).where(Question.is_active == True)

    if chap_id:
        query = query.where(Question.chapter_id == subject_id)
    if class_id:
        query = query.join(Class).where(Class.id == class_id)
    if subject_id:
        query = query.join(Subject).where(Subject.id == subject_id)
    if difficulty_level:
        query = query.where(Question.difficulty_level == difficulty_level)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
