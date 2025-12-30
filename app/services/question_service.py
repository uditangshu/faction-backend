"""Question bank service"""

import random
from datetime import datetime, timedelta, time
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_
from typing import List, Optional, Tuple, Dict, Any

from app.models.Basequestion import Topic, Question, QuestionType, DifficultyLevel, Chapter, Subject
from app.models.user import TargetExam
from app.models.qotd import QOTD


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
        mcq_correct_option: Optional[List[int]] = None,
        scq_options: Optional[List[str]] = None,
        scq_correct_options: Optional[int] = None,
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
        mcq_correct_option: Optional[List[int]] = None,
        scq_options: Optional[List[str]] = None,
        scq_correct_options: Optional[int] = None,
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

    async def get_qotd_questions(
        self, 
        class_id: UUID, 
        timezone_offset: int
    ) -> List[Tuple[Question, str]]:
        """
        Get Question of the Day: 3 random questions from 3 different subjects.
        Checks if QOTD exists for today (in user's timezone) before creating a new one.
        
        Args:
            class_id: Class ID to filter questions by user's class
            timezone_offset: User's timezone offset in minutes from UTC
        
        Returns:
            List of tuples (question, subject_name), each from a different subject
        """
        # Calculate user's local time
        utc_now = datetime.utcnow()
        user_local_time = utc_now + timedelta(minutes=timezone_offset)
        user_local_date = user_local_time.date()
        
        # Calculate the start of today in user's timezone (00:00:00) converted to UTC
        today_start_utc = datetime.combine(user_local_date, time(0, 0, 0)) - timedelta(minutes=timezone_offset)
        # Calculate the start of tomorrow in user's timezone (00:00:00) converted to UTC
        tomorrow_start_utc = today_start_utc + timedelta(days=1)
        
        # Check if current UTC time is before tomorrow's midnight in user's timezone
        # This means we're still in the same day, so check for existing QOTD
        is_before_midnight = utc_now < tomorrow_start_utc
        
        # Only check for existing QOTD if we're still in the same day (before midnight)
        if is_before_midnight:
            # Check for QOTD created today (in user's timezone) for this class_id
            qotd_query = (
                select(QOTD)
                .where(
                    and_(
                        QOTD.class_id == class_id,
                        QOTD.created_at >= today_start_utc
                    )
                )
                .order_by(QOTD.created_at.desc())
                .limit(1)
            )
            qotd_result = await self.db.execute(qotd_query)
            existing_qotd = qotd_result.scalar_one_or_none()
            
            if existing_qotd and existing_qotd.questions:
                # Return questions from existing QOTD
                # Need to fetch Question objects from the stored IDs
                question_ids = [UUID(q.get("id")) for q in existing_qotd.questions if q.get("id")]
                if question_ids:
                    questions_result = await self.db.execute(
                        select(Question).where(Question.id.in_(question_ids))
                    )
                    questions = list(questions_result.scalars().all())
                    
                    # Map questions to their subject names from stored data
                    qotd_questions = []
                    for q_data in existing_qotd.questions:
                        q_id = UUID(q_data.get("id"))
                        subject_name = q_data.get("subject_name", "")
                        # Find matching question
                        question = next((q for q in questions if q.id == q_id), None)
                        if question:
                            qotd_questions.append((question, subject_name))
                    
                    if qotd_questions:
                        return qotd_questions
            
            # If time is before midnight and QOTD does not exist, create one, store it, and return
            # Generate new QOTD questions
            qotd_questions = await self._generate_qotd_questions(class_id)
            
            # Store in database
            if qotd_questions:
                # Convert questions to JSON format
                questions_json = []
                for question, subject_name in qotd_questions:
                    # Get question details as dict with JSON serialization mode to convert UUIDs to strings
                    from app.schemas.question import QuestionDetailedResponse
                    question_dict = QuestionDetailedResponse.model_validate(question).model_dump(mode='json')
                    question_dict["subject_name"] = subject_name
                    questions_json.append(question_dict)
                
                new_qotd = QOTD(
                    class_id=class_id,
                    questions=questions_json
                )
                self.db.add(new_qotd)
                await self.db.commit()
            
            return qotd_questions
        
        # If past midnight (new day), generate new QOTD questions
        qotd_questions = await self._generate_qotd_questions(class_id)
        
        # Store in database
        if qotd_questions:
            # Convert questions to JSON format
            questions_json = []
            for question, subject_name in qotd_questions:
                # Get question details as dict with JSON serialization mode to convert UUIDs to strings
                from app.schemas.question import QuestionDetailedResponse
                question_dict = QuestionDetailedResponse.model_validate(question).model_dump(mode='json')
                question_dict["subject_name"] = subject_name
                questions_json.append(question_dict)
            
            new_qotd = QOTD(
                class_id=class_id,
                questions=questions_json
            )
            self.db.add(new_qotd)
            await self.db.commit()
        
        return qotd_questions
    
    async def _generate_qotd_questions(self, class_id: UUID) -> List[Tuple[Question, str]]:
        """
        Generate Question of the Day: 3 random questions from 3 different subjects.
        
        Args:
            class_id: Class ID to filter questions by user's class
        
        Returns:
            List of tuples (question, subject_name), each from a different subject
        """
        # Get all distinct subjects that have questions, filtered by class
        subject_query = (
            select(Chapter.subject_id)
            .join(Topic, Topic.chapter_id == Chapter.id)
            .join(Question, Question.topic_id == Topic.id)
            .join(Subject, Chapter.subject_id == Subject.id)
            .where(Subject.class_id == class_id)
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
        
        # For each selected subject, get a random question with subject name
        for subject_id in selected_subject_ids:
            # Get all questions for this subject with subject info
            question_query = (
                select(Question, Subject.subject_type)
                .join(Topic, Question.topic_id == Topic.id)
                .join(Chapter, Topic.chapter_id == Chapter.id)
                .join(Subject, Chapter.subject_id == Subject.id)
                .where(Chapter.subject_id == subject_id)
            )
            result = await self.db.execute(question_query)
            questions_with_subjects = list(result.all())
            
            if questions_with_subjects:
                # Randomly select one question from this subject
                random_question, subject_type = random.choice(questions_with_subjects)
                qotd_questions.append((random_question, subject_type.value))
        
        return qotd_questions
