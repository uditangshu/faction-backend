"""Question bank service"""

import json
from asyncio import gather
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional, Tuple

from app.models.question import Question, QuestionOption, QuestionType
from app.models.attempt import QuestionAttempt
from app.models.subject import Subject, Topic
from app.utils.exceptions import NotFoundException


class QuestionService:
    """Service for question operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_questions(
        self,
        subject_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
        difficulty_level: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Question]:
        """
        Get list of questions with filters.

        Args:
            subject_id: Filter by subject
            topic_id: Filter by topic
            difficulty_level: Filter by difficulty (1-5)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of questions
        """
        query = select(Question).where(Question.is_active == True)

        if subject_id:
            query = query.where(Question.subject_id == subject_id)
        if topic_id:
            query = query.where(Question.topic_id == topic_id)
        if difficulty_level:
            query = query.where(Question.difficulty_level == difficulty_level)

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_question_by_id(self, question_id: UUID) -> Question:
        """
        Get question by ID.

        Args:
            question_id: Question UUID

        Returns:
            Question object

        Raises:
            NotFoundException: If question not found
        """
        result = await self.db.execute(
            select(Question).where(Question.id == question_id, Question.is_active == True)
        )
        question = result.scalar_one_or_none()

        if not question:
            raise NotFoundException("Question not found")

        return question

    async def get_question_with_options(self, question_id: UUID) -> Tuple[Question, List[QuestionOption]]:
        """
        Get question by ID with options in a single optimized query.

        Args:
            question_id: Question UUID

        Returns:
            Tuple of (Question, List[QuestionOption])

        Raises:
            NotFoundException: If question not found
        """
        # Execute both queries concurrently for better performance
        question_result, options_result = await gather(
            self.db.execute(
                select(Question).where(Question.id == question_id, Question.is_active == True)
            ),
            self.db.execute(
                select(QuestionOption)
                .where(QuestionOption.question_id == question_id)
                .order_by(QuestionOption.option_order)
            )
        )
        
        question = question_result.scalar_one_or_none()
        if not question:
            raise NotFoundException("Question not found")
        
        options = list(options_result.scalars().all())
        return question, options

    async def get_question_options(self, question_id: UUID) -> List[QuestionOption]:
        """Get options for a question"""
        result = await self.db.execute(
            select(QuestionOption)
            .where(QuestionOption.question_id == question_id)
            .order_by(QuestionOption.option_order)
        )
        return list(result.scalars().all())

    async def evaluate_answer(
        self, question: Question, user_answer: str, options: List[QuestionOption]
    ) -> tuple[bool, int]:
        """
        Evaluate user's answer.

        Args:
            question: Question object
            user_answer: User's answer
            options: Question options

        Returns:
            Tuple of (is_correct, marks_obtained)
        """
        is_correct = False
        marks = 0

        if question.question_type == QuestionType.MCQ:
            # Find correct option
            correct_option = next((opt for opt in options if opt.is_correct), None)
            if correct_option and user_answer == correct_option.option_label:
                is_correct = True
                marks = question.points

        elif question.question_type == QuestionType.NUMERICAL:
            try:
                user_value = float(user_answer)
                correct_value = question.correct_numerical_value
                tolerance = question.numerical_tolerance or 0.01

                if correct_value is not None and abs(user_value - correct_value) <= tolerance:
                    is_correct = True
                    marks = question.points
            except (ValueError, TypeError):
                is_correct = False

        elif question.question_type == QuestionType.MULTI_SELECT:
            # Parse user answer as list
            try:
                user_options = json.loads(user_answer) if isinstance(user_answer, str) else user_answer
                correct_options = sorted([opt.option_label for opt in options if opt.is_correct])
                user_options_sorted = sorted(user_options)

                if correct_options == user_options_sorted:
                    is_correct = True
                    marks = question.points
            except (json.JSONDecodeError, TypeError):
                is_correct = False

        return is_correct, marks

    async def submit_answer(
        self, user_id: UUID, question_id: UUID, user_answer: str, time_taken: int
    ) -> dict:
        """
        Submit and evaluate user's answer.

        Args:
            user_id: User UUID
            question_id: Question UUID
            user_answer: User's answer
            time_taken: Time taken in seconds

        Returns:
            Dict with evaluation results

        Raises:
            NotFoundException: If question not found
        """
        # Get question and options
        question = await self.get_question_by_id(question_id)
        options = await self.get_question_options(question_id)

        # Evaluate answer
        is_correct, marks = await self.evaluate_answer(question, user_answer, options)

        # Create attempt record
        attempt = QuestionAttempt(
            user_id=user_id,
            question_id=question_id,
            user_answer=user_answer,
            is_correct=is_correct,
            marks_obtained=marks,
            time_taken=time_taken,
        )

        self.db.add(attempt)

        # Update question stats
        question.attempt_count += 1
        if is_correct:
            question.solved_count += 1

        await self.db.commit()
        await self.db.refresh(attempt)

        return {
            "attempt_id": attempt.id,
            "is_correct": is_correct,
            "marks_obtained": marks,
            "time_taken": time_taken,
            "explanation": question.explanation if is_correct or True else None,  # Always show for now
        }

