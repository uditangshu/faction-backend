"""Question bank service"""

import random
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List, Optional, Tuple

from app.models.Basequestion import Topic, Question, QuestionType, DifficultyLevel, Chapter, Subject
from app.models.user import TargetExam


class QuestionService:
    """Service for question operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_question(
        self,
        topic_id: UUID,
        type: QuestionType,
        difficulty: DifficultyLevel,
        exam_type: List[TargetExam],
        question_text: str,
        marks: int,
        solution_text: str,
        question_image: Optional[str] = None,
        integer_answer: Optional[int] = None,
        mcq_options: Optional[List[str]] = None,
        mcq_correct_option: Optional[int] = None,
        scq_options: Optional[List[str]] = None,
        scq_correct_options: Optional[List[int]] = None,
    ) -> Question:
        """Create a new question"""
        question = Question(
            topic_id=topic_id,
            type=type,
            difficulty=difficulty,
            exam_type=exam_type,
            question_text=question_text,
            marks=marks,
            solution_text=solution_text,
            question_image=question_image,
            integer_answer=integer_answer,
            mcq_options=mcq_options,
            mcq_correct_option=mcq_correct_option,
            scq_options=scq_options,
            scq_correct_options=scq_correct_options,
            questions_solved=0,
        )
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def get_questions(
        self,
        topic_id: Optional[UUID] = None,
        chapter_id: Optional[UUID] = None,
        subject_id: Optional[UUID] = None,
        difficulty_level: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Question], int]:
        """
        Get list of questions with filters and total count.

        Returns:
            Tuple of (questions list, total count)
        """
        query = select(Question)
        count_query = select(func.count(Question.id))

        if topic_id:
            query = query.where(Question.topic_id == topic_id)
            count_query = count_query.where(Question.topic_id == topic_id)
        if chapter_id:
            query = query.join(Topic).where(Topic.chapter_id == chapter_id)
            count_query = count_query.join(Topic).where(Topic.chapter_id == chapter_id)
        if subject_id:
            query = query.join(Topic).join(Chapter).where(Chapter.subject_id == subject_id)
            count_query = count_query.join(Topic).join(Chapter).where(Chapter.subject_id == subject_id)
        if difficulty_level:
            query = query.where(Question.difficulty == difficulty_level)
            count_query = count_query.where(Question.difficulty == difficulty_level)

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        
        return list(result.scalars().all()), total

    async def get_question_by_id(self, question_id: UUID) -> Optional[Question]:
        """Get question by ID"""
        result = await self.db.execute(
            select(Question).where(Question.id == question_id)
        )
        return result.scalar_one_or_none()

    async def update_question(
        self,
        question_id: UUID,
        topic_id: Optional[UUID] = None,
        type: Optional[QuestionType] = None,
        difficulty: Optional[DifficultyLevel] = None,
        exam_type: Optional[List[TargetExam]] = None,
        question_text: Optional[str] = None,
        marks: Optional[int] = None,
        solution_text: Optional[str] = None,
        question_image: Optional[str] = None,
        integer_answer: Optional[int] = None,
        mcq_options: Optional[List[str]] = None,
        mcq_correct_option: Optional[int] = None,
        scq_options: Optional[List[str]] = None,
        scq_correct_options: Optional[List[int]] = None,
    ) -> Optional[Question]:
        """Update an existing question"""
        question = await self.get_question_by_id(question_id)
        if not question:
            return None

        # Update only provided fields
        if topic_id is not None:
            question.topic_id = topic_id
        if type is not None:
            question.type = type
        if difficulty is not None:
            question.difficulty = difficulty
        if exam_type is not None:
            question.exam_type = exam_type
        if question_text is not None:
            question.question_text = question_text
        if marks is not None:
            question.marks = marks
        if solution_text is not None:
            question.solution_text = solution_text
        if question_image is not None:
            question.question_image = question_image
        if integer_answer is not None:
            question.integer_answer = integer_answer
        if mcq_options is not None:
            question.mcq_options = mcq_options
        if mcq_correct_option is not None:
            question.mcq_correct_option = mcq_correct_option
        if scq_options is not None:
            question.scq_options = scq_options
        if scq_correct_options is not None:
            question.scq_correct_options = scq_correct_options

        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def delete_question(self, question_id: UUID) -> bool:
        """Delete a question by ID"""
        question = await self.get_question_by_id(question_id)
        if not question:
            return False
        
        stmt = delete(Question).where(Question.id == question_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def get_qotd_questions(self) -> List[Question]:
        """
        Get Question of the Day: 3 random questions from 3 different subjects.
        
        Returns:
            List of 3 questions, each from a different subject
        """
        # Get all distinct subjects that have questions
        subject_query = (
            select(Chapter.subject_id)
            .join(Topic, Topic.chapter_id == Chapter.id)
            .join(Question, Question.topic_id == Topic.id)
            .distinct()
        )
        subject_result = await self.db.execute(subject_query)
        subject_ids = [row[0] for row in subject_result.all() if row[0] is not None]
        
        if len(subject_ids) == 0:
            return []
        
        # Randomly select up to 3 different subjects
        num_subjects_to_select = min(3, len(subject_ids))
        selected_subject_ids = random.sample(subject_ids, num_subjects_to_select)
        
        qotd_questions = []
        
        # For each selected subject, get a random question
        for subject_id in selected_subject_ids:
            # Get all questions for this subject
            question_query = (
                select(Question)
                .join(Topic, Question.topic_id == Topic.id)
                .join(Chapter, Topic.chapter_id == Chapter.id)
                .where(Chapter.subject_id == subject_id)
            )
            result = await self.db.execute(question_query)
            questions = list(result.scalars().all())
            
            if questions:
                # Randomly select one question from this subject
                random_question = random.choice(questions)
                qotd_questions.append(random_question)
        
        return qotd_questions
