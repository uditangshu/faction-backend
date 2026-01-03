"""Scholarship Service"""

import random
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.models.Basequestion import Question, Topic, Chapter, Subject, QuestionType, QuestionType
from app.models.user import TargetExam
from app.models.scholarship import Scholarship, AttemptStatus, ScholarshipResult
from app.models.linking import ScholarshipQuestion
from app.exceptions.http_exceptions import BadRequestException, NotFoundException
from app.db.attempt_calls import create_attempt


class ScholarshipService:
    """Service for scholarship test operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_scholarship_test(
        self,
        user_id: UUID,
        class_id: UUID,
        exam_type: TargetExam,
        time_required: int,
    ) -> tuple[Scholarship, List[Question]]:
        """
        Create a scholarship test with 5 questions from each of 3 randomly selected subjects (15 questions total).
        
        Args:
            user_id: User ID who owns the test
            class_id: Class ID to filter subjects
            exam_type: Exam type to filter subjects and questions
            time_required: Time required for the test in seconds
            
        Returns:
            Tuple of (Scholarship instance, List of questions)
            
        Raises:
            NotFoundException: If class not found or not enough subjects/questions
            BadRequestException: If user already has a scholarship test
        """
        # Check if user already has a scholarship test
        existing_scholarship_result = await self.db.execute(
            select(Scholarship).where(Scholarship.user_id == user_id)
        )
        existing_scholarship = existing_scholarship_result.scalar_one_or_none()
        if existing_scholarship:
            raise BadRequestException("User already has a scholarship test. Please complete or delete the existing one first.")

        # Validate class exists
        from app.models.Basequestion import Class
        class_result = await self.db.execute(
            select(Class).where(Class.id == class_id)
        )
        class_obj = class_result.scalar_one_or_none()
        if not class_obj:
            raise NotFoundException(f"Class with ID {class_id} not found")

        # Get all subjects for the class and exam_type
        query = select(Subject).where(
            Subject.class_id == class_id
        ).where(
            cast(Subject.exam_type, JSONB).contains([exam_type.value])
        )
        result = await self.db.execute(query)
        all_subjects = list(result.scalars().all())

        if len(all_subjects) < 3:
            raise NotFoundException(
                f"Not enough subjects found for class {class_id} and exam type {exam_type.value}. "
                f"Found {len(all_subjects)} subjects, but need at least 3."
            )

        # Randomly select 3 subjects
        selected_subjects = random.sample(all_subjects, 3)
        selected_subject_ids = [s.id for s in selected_subjects]

        # Get 5 questions from EACH of the 3 selected subjects (15 questions total)
        questions = []
        for subject_id in selected_subject_ids:
            query = select(Question)
            query = query.join(Topic, Question.topic_id == Topic.id)
            query = query.join(Chapter, Topic.chapter_id == Chapter.id)
            query = query.join(Subject, Chapter.subject_id == Subject.id)
            query = query.where(Subject.id == subject_id)
            query = query.where(
                cast(Question.exam_type, JSONB).contains([exam_type.value])
            )
            query = query.order_by(func.random()).limit(5)
            
            result = await self.db.execute(query)
            subject_questions = list(result.scalars().all())
            
            # Check if we have enough questions for this subject
            if len(subject_questions) < 5:
                raise NotFoundException(
                    f"Not enough questions found for subject. Found {len(subject_questions)} questions, but need 5. "
                    f"Please ensure there are enough questions in the selected subjects for exam type {exam_type.value}."
                )
            
            questions.extend(subject_questions)

        # Create the scholarship test
        scholarship = Scholarship(
            user_id=user_id,
            class_id=class_id,
            exam_type=exam_type,
            time_assigned=time_required,
            status=AttemptStatus.not_started,
        )
        self.db.add(scholarship)
        await self.db.flush()  # Get the scholarship ID

        # Create scholarship-question links
        scholarship_questions = [
            ScholarshipQuestion(
                scholarship_id=scholarship.id,
                question_id=question.id
            )
            for question in questions
        ]
        self.db.add_all(scholarship_questions)

        await self.db.commit()
        await self.db.refresh(scholarship)

        return scholarship, questions

    async def get_scholarship_by_id(
        self,
        scholarship_id: UUID,
        user_id: UUID,
    ) -> Optional[Scholarship]:
        """
        Get a scholarship test by ID with all questions.
        
        Args:
            scholarship_id: Scholarship test ID
            user_id: User ID to verify ownership
            
        Returns:
            Scholarship with questions loaded, or None if not found
        """
        result = await self.db.execute(
            select(Scholarship)
            .where(Scholarship.id == scholarship_id, Scholarship.user_id == user_id)
            .options(
                selectinload(Scholarship.questions)
                .selectinload(ScholarshipQuestion.question)
            )
        )
        return result.scalar_one_or_none()

    def _validate_answer(self, question_data: dict, user_answer: List[str]) -> tuple[bool, int]:
        """Validate user answer and calculate marks (same logic as contest worker)"""
        is_correct = False
        marks_obtained = 0
        
        if question_data["type"] == QuestionType.INTEGER:
            if user_answer and len(user_answer) == 1:
                try:
                    user_int = int(user_answer[0])
                    if question_data["integer_answer"] is not None:
                        if user_int == question_data["integer_answer"]:
                            is_correct = True
                            marks_obtained = question_data["marks"]
                        else:
                            marks_obtained = -1
                except ValueError:
                    marks_obtained = -1
            else:
                marks_obtained = -1
                
        elif question_data["type"] == QuestionType.MCQ:
            if question_data["mcq_correct_option"] is not None and question_data["mcq_options"] is not None:
                try:
                    user_indices = set()
                    for ans in user_answer:
                        for idx, option_text in enumerate(question_data["mcq_options"]):
                            if ans.strip() == option_text.strip():
                                user_indices.add(idx)
                                break
                    
                    correct_indices = set(question_data["mcq_correct_option"])
                    incorrect_selected = user_indices - correct_indices
                    
                    if len(incorrect_selected) > 0:
                        marks_obtained = -2
                    else:
                        correct_selected = user_indices & correct_indices
                        if len(correct_selected) == len(correct_indices):
                            is_correct = True
                            marks_obtained = question_data["marks"]
                        else:
                            marks_obtained = len(correct_selected)
                except (ValueError, TypeError, IndexError):
                    marks_obtained = 0
                    
        elif question_data["type"] == QuestionType.SCQ:
            if user_answer and len(user_answer) == 1:
                try:
                    user_index = None
                    if question_data.get("scq_options") is not None:
                        for idx, option_text in enumerate(question_data["scq_options"]):
                            if user_answer[0].strip() == option_text.strip():
                                user_index = idx
                                break
                    
                    if question_data["scq_correct_options"] is not None and user_index is not None:
                        if user_index == question_data["scq_correct_options"]:
                            is_correct = True
                            marks_obtained = question_data["marks"]
                        else:
                            marks_obtained = -1
                    else:
                        marks_obtained = -1
                except (ValueError, TypeError, IndexError):
                    marks_obtained = -1
            else:
                marks_obtained = -1
                
        elif question_data["type"] == QuestionType.MATCH:
            if question_data["mcq_correct_option"] is not None and question_data.get("mcq_options") is not None:
                try:
                    user_indices = []
                    for ans in user_answer:
                        for idx, option_text in enumerate(question_data["mcq_options"]):
                            if ans.strip() == option_text.strip():
                                user_indices.append(idx)
                                break
                    
                    user_indices = sorted(user_indices)
                    correct_indices = sorted(question_data["mcq_correct_option"])
                    if user_indices == correct_indices:
                        is_correct = True
                        marks_obtained = question_data["marks"]
                    else:
                        marks_obtained = -1
                except (ValueError, TypeError, IndexError):
                    marks_obtained = -1
            else:
                marks_obtained = -1
        
        return is_correct, marks_obtained

    async def submit_scholarship_test(
        self,
        scholarship_id: UUID,
        user_id: UUID,
        submissions_data: List[dict],
    ) -> ScholarshipResult:
        """
        Submit scholarship test and calculate results.
        
        Args:
            scholarship_id: Scholarship test ID
            user_id: User ID
            submissions_data: List of submission dicts with question_id, user_answer, time_taken
            
        Returns:
            ScholarshipResult instance
        """
        # Get scholarship with questions
        scholarship = await self.get_scholarship_by_id(scholarship_id, user_id)
        if not scholarship:
            raise NotFoundException(f"Scholarship test with ID {scholarship_id} not found")
        
        if scholarship.status == AttemptStatus.finished:
            raise BadRequestException("Scholarship test has already been submitted")
        
        # Get all question IDs from scholarship
        question_ids = {sq.question_id for sq in scholarship.questions}
        total_questions = len(question_ids)
        
        # Fetch all questions
        result = await self.db.execute(
            select(Question).where(Question.id.in_(question_ids))
        )
        questions_list = result.scalars().all()
        
        # Prepare question data
        questions_data = {}
        for q in questions_list:
            questions_data[q.id] = {
                "type": q.type,
                "integer_answer": q.integer_answer,
                "mcq_options": q.mcq_options,
                "mcq_correct_option": q.mcq_correct_option,
                "scq_options": q.scq_options,
                "scq_correct_options": q.scq_correct_options,
                "marks": q.marks,
            }
        
        # Calculate total marks
        total_marks = sum(q.marks for q in questions_list)
        
        # Process submissions
        total_score = 0.0
        correct_count = 0
        incorrect_count = 0
        total_time = 0
        attempted_question_ids = set()
        
        for submission in submissions_data:
            question_id = UUID(submission["question_id"])
            if question_id not in question_ids:
                raise BadRequestException(f"Question {question_id} is not part of this scholarship test")
            
            question_data = questions_data.get(question_id)
            if not question_data:
                continue
            
            # Validate answer
            is_correct, marks_obtained = self._validate_answer(
                question_data, submission["user_answer"]
            )
            
            # Create attempt
            await create_attempt(
                db=self.db,
                user_id=user_id,
                question_id=question_id,
                user_answer=submission["user_answer"],
                is_correct=is_correct,
                marks_obtained=marks_obtained,
                time_taken=submission["time_taken"],
                hint_used=False,
            )
            
            # Update counters
            total_score += marks_obtained
            total_time += submission.get("time_taken", 0)
            attempted_question_ids.add(question_id)
            if is_correct:
                correct_count += 1
            else:
                incorrect_count += 1
        
        # Calculate final metrics
        unattempted = total_questions - len(attempted_question_ids)
        accuracy = (correct_count / len(attempted_question_ids) * 100) if attempted_question_ids else 0.0
        
        # Create scholarship result
        scholarship_result = ScholarshipResult(
            user_id=user_id,
            scholarship_id=scholarship_id,
            score=total_score,
            total_marks=total_marks,
            time_taken=total_time,
            correct=correct_count,
            incorrect=incorrect_count,
            unattempted=unattempted,
            accuracy=accuracy,
        )
        self.db.add(scholarship_result)
        
        # Update scholarship status
        scholarship.status = AttemptStatus.finished
        scholarship.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(scholarship_result)
        
        return scholarship_result

    async def get_scholarship_result(
        self,
        scholarship_id: UUID,
        user_id: UUID,
    ) -> ScholarshipResult:
        """
        Get scholarship result by scholarship ID.
        
        Args:
            scholarship_id: Scholarship test ID
            user_id: User ID to verify ownership
            
        Returns:
            ScholarshipResult instance
            
        Raises:
            NotFoundException: If scholarship or result not found
        """
        # First verify scholarship exists and belongs to user
        scholarship_result_query = await self.db.execute(
            select(Scholarship).where(
                Scholarship.id == scholarship_id,
                Scholarship.user_id == user_id
            )
        )
        scholarship = scholarship_result_query.scalar_one_or_none()
        
        if not scholarship:
            raise NotFoundException(f"Scholarship test with ID {scholarship_id} not found for this user")
        
        # Get scholarship result
        result_query = await self.db.execute(
            select(ScholarshipResult).where(
                ScholarshipResult.scholarship_id == scholarship_id,
                ScholarshipResult.user_id == user_id
            )
        )
        result = result_query.scalar_one_or_none()
        
        if not result:
            raise NotFoundException(f"Scholarship result not found for scholarship ID {scholarship_id}")
        
        return result

