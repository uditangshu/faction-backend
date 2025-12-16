"""Custom Test Service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,cast,exists,not_,func
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional, Tuple

from app.models.custom_test import CustomTest, CustomTestAnalysis, AttemptStatus
from app.models.linking import CustomTestQuestion
from app.models.attempt import QuestionAttempt
from app.db.custom_test_call import (
    create_custom_test,
    get_custom_test_by_id,
    get_custom_test_with_questions,
    get_user_custom_tests,
    update_custom_test_status,
    delete_custom_test,
    get_test_questions,
    create_custom_test_analysis,
    get_analysis_by_id,
    delete_analysis,
    get_user_test_stats,
)
from app.schemas.custom_test import (
    QuestionNumber,
    QuestionAppearance,
    QuestionStatus,
    QuestionAnswerSubmit,
    QuestionResultResponse,
)
from app.models.Basequestion import TargetExam, Topic, QuestionType, Subject, Question, Chapter
from app.models.pyq import PreviousYearProblems

class CustomTestService:
    """Service for custom test operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Custom Test Methods ====================

    async def create_test(
        self,
        user_id: UUID,
        exam_type: TargetExam,
        chapters: List[UUID],
        question_status: QuestionStatus,
        number_of_question: QuestionNumber,
        time_duration: int,
        question_type: QuestionAppearance
    ) -> CustomTest:
        """Create a new custom test with questions"""
        # Validate that all chapters and subjects exist
        
        for chapter_id in chapters:
            result = await self.db.execute(
                select(Chapter).where(Chapter.id==chapter_id)
            )
            if not result.scalar_one_or_none():
                    raise ValueError(f"Chapter with ID {chapter_id} not found")

        #filter out all the required problems with tags
        #pass the question ids to the create_custom_test

        query = (
        select(Question, QuestionAttempt)
        .join(Topic, Question.topic_id == Topic.id)
        .join(Chapter, Topic.chapter_id == Chapter.id)
        .where(Chapter.id.in_(chapters))
        .where(cast(Question.exam_type, JSONB).contains([exam_type]))
        )

        if question_status==QuestionStatus.INCORRECT:
            query=query.join(QuestionAttempt, QuestionAttempt.question_id==Question.id
            ).where(QuestionAttempt.is_correct == False)
        elif question_status==QuestionStatus.SOLVED:
            query=query.join(QuestionAttempt, QuestionAttempt.question_id==Question.id
            ).where(QuestionAttempt.is_correct == True)
        elif question_status==QuestionStatus.UNSOLVED:
            query=query.outerjoin(QuestionAttempt, QuestionAttempt.question_id!=Question.id
                            ).where(QuestionAttempt.id.is_(None))
        
        #filtering Based over pyq or not

        if question_type == QuestionAppearance.PYQs:
            query = query.where(
                exists().where(PreviousYearProblems.question_id == Question.id)
            )
        elif question_type == QuestionAppearance.NON_PYQs:
            query = query.where(
                not_(exists().where(PreviousYearProblems.question_id == Question.id))
            )

        result = await self.db.execute(query)
        questions = result.scalars().all()

        question_ids = []
        question_ids = [q.id for q in questions][:number_of_question]

        return await create_custom_test(
            self.db,
            user_id=user_id,
            question_ids=question_ids,
            time_assigned=time_duration,
            status=AttemptStatus.not_started,
        )

    async def get_test_by_id(self, test_id: UUID) -> Optional[CustomTest]:
        """Get a custom test by ID"""
        return await get_custom_test_by_id(self.db, test_id)

    async def get_test_with_questions(self, test_id: UUID) -> Optional[CustomTest]:
        """Get a custom test with all its questions"""
        return await get_custom_test_with_questions(self.db, test_id)

    async def get_user_tests(
        self,
        user_id: UUID,
        status: Optional[AttemptStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[CustomTest], int]:
        """Get all custom tests for a user with pagination"""
        return await get_user_custom_tests(self.db, user_id, status, skip, limit)

    async def start_test(self, test_id: UUID, user_id: UUID) -> Optional[CustomTest]:
        """Start a custom test (change status to active)"""
        test = await self.get_test_by_id(test_id)
        if not test:
            return None
        
        # Verify ownership
        if test.user_id != user_id:
            return None
        
        # Only allow starting if not_started
        if test.status != AttemptStatus.not_started:
            raise ValueError(f"Test cannot be started. Current status: {test.status}")
        
        return await update_custom_test_status(self.db, test_id, AttemptStatus.active)

    async def update_test_status(
        self,
        test_id: UUID,
        user_id: UUID,
        status: AttemptStatus,
    ) -> Optional[CustomTest]:
        """Update the status of a custom test"""
        test = await self.get_test_by_id(test_id)
        if not test:
            return None
        
        # Verify ownership
        if test.user_id != user_id:
            return None
        
        return await update_custom_test_status(self.db, test_id, status)

    async def delete_test(self, test_id: UUID, user_id: UUID) -> bool:
        """Delete a custom test"""
        test = await self.get_test_by_id(test_id)
        if not test:
            return False
        
        # Verify ownership
        if test.user_id != user_id:
            return False
        
        return await delete_custom_test(self.db, test_id)

    async def get_test_question_count(self, test_id: UUID) -> int:
        """Get the number of questions in a test"""
        result = await self.db.execute(
            select(func.count(CustomTestQuestion.id))
            .where(CustomTestQuestion.test_id == test_id)
        )
        return result.scalar() or 0

    async def get_test_questions(self, test_id: UUID) -> List[Question]:
        """Get all questions for a test"""
        return await get_test_questions(self.db, test_id)

    async def get_test_attempts(
        self,
        test_id: UUID,
        user_id: UUID,
    ) -> Tuple[List[QuestionAttempt], dict]:
        """
        Get all question attempts for a custom test.
        Returns tuple of (attempts list, summary stats)
        """
        # First verify the test exists and belongs to user
        test = await self.get_test_by_id(test_id)
        if not test:
            raise ValueError("Test not found")
        
        if test.user_id != user_id:
            raise ValueError("You don't have permission to view this test")
        
        # Get all question IDs for this test
        question_ids_result = await self.db.execute(
            select(CustomTestQuestion.question_id)
            .where(CustomTestQuestion.test_id == test_id)
        )
        question_ids = [row[0] for row in question_ids_result.all()]
        
        if not question_ids:
            return [], {
                "total_attempts": 0,
                "total_correct": 0,
                "total_incorrect": 0,
                "total_marks_obtained": 0,
                "total_time_taken": 0,
            }
        
        # Get all attempts for these questions by this user
        result = await self.db.execute(
            select(QuestionAttempt)
            .where(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.question_id.in_(question_ids),
            )
            .order_by(QuestionAttempt.attempted_at.desc())
        )
        attempts = list(result.scalars().all())
        
        # Calculate summary stats
        total_correct = sum(1 for a in attempts if a.is_correct)
        total_incorrect = len(attempts) - total_correct
        total_marks = sum(a.marks_obtained for a in attempts)
        total_time = sum(a.time_taken for a in attempts)
        
        summary = {
            "total_attempts": len(attempts),
            "total_correct": total_correct,
            "total_incorrect": total_incorrect,
            "total_marks_obtained": total_marks,
            "total_time_taken": total_time,
        }
        
        return attempts, summary

    # ==================== Submit Test & Scoring ====================

    async def submit_test(
        self,
        test_id: UUID,
        user_id: UUID,
        answers: List[QuestionAnswerSubmit],
        total_time_spent: int,
    ) -> Tuple[CustomTestAnalysis, List[QuestionResultResponse]]:
        """Submit a custom test and calculate results"""
        # Get the test
        test = await self.get_test_with_questions(test_id)
        if not test:
            raise ValueError("Test not found")
        
        # Verify ownership
        if test.user_id != user_id:
            raise ValueError("You don't have permission to submit this test")
        
        # Verify test is active or not_started
        if test.status == AttemptStatus.finished:
            raise ValueError("Test has already been submitted")
        
        # Get all questions for this test
        questions = await self.get_test_questions(test_id)
        question_map = {q.id: q for q in questions}
        
        # Create a map of submitted answers
        answer_map = {a.question_id: a for a in answers}
        
    
        # Calculate results
        results: List[QuestionResultResponse] = []
        total_marks = 0
        marks_obtained = 0
        correct_count = 0
        incorrect_count = 0
        unattempted_count = 0
        
        #save attempt
        attempts: List[QuestionAttempt]= []
        
        for question in questions:
            total_marks += question.marks
            answer = answer_map.get(question.id)
            
            # Get the correct answer based on question type
            correct_answer = self._get_correct_answer(question)
            
            if not answer or answer.user_answer is None or len(answer.user_answer) == 0:
                # Unattempted
                unattempted_count += 1
                results.append(QuestionResultResponse(
                    question_id=question.id,
                    user_answer=None,
                    correct_answer=correct_answer,
                    is_correct=False,
                    marks_obtained=0,
                    marks_possible=question.marks,
                ))
                
            else:
                # Check if answer is correct
                is_correct = self._check_answer(question, answer.user_answer)
                
                if is_correct:
                    correct_count += 1
                    marks_obtained += question.marks
                else:
                    incorrect_count += 1
                
                results.append(QuestionResultResponse(
                    question_id=question.id,
                    user_answer=answer.user_answer,
                    correct_answer=correct_answer,
                    is_correct=is_correct,
                    marks_obtained=question.marks if is_correct else 0,
                    marks_possible=question.marks,
                ))

                attempts.append(QuestionAttempt(
                    user_id=user_id,
                    question_id=question.id,
                    user_answer=answer.user_answer,
                    is_correct=is_correct,
                    marks_obtained=question.marks if is_correct else 0,
                    time_taken=answer.time_spent,
                    explanation_viewed=False,
                    hint_used=False
                ))

        self.db.add_all(attempts)
        await self.db.commit()

        for attempt in attempts:
            await self.db.refresh(attempt)

        
        # Mark test as finished
        await update_custom_test_status(self.db, test_id, AttemptStatus.finished)
        
        # Create analysis
        analysis = await create_custom_test_analysis(
            self.db,
            user_id=user_id,
            custom_test_id=test_id,
            marks_obtained=marks_obtained,
            total_marks=total_marks,
            total_time_spent=total_time_spent,
            correct=correct_count,
            incorrect=incorrect_count,
            unattempted=unattempted_count,
        )
        
        return analysis, results

    def _get_correct_answer(self, question: Question) -> Optional[List[str]]:
        """Get the correct answer for a question"""
        if question.type == QuestionType.INTEGER:
            if question.integer_answer is not None:
                return [str(question.integer_answer)]
        elif question.type == QuestionType.MCQ:
            if question.mcq_correct_option and question.mcq_options:
                answers = []
                try:
                    for idx in question.mcq_correct_option:
                        answers.append(question.mcq_options[idx])
                except (IndexError, TypeError):
                    return None
                return answers
        elif question.type == QuestionType.SCQ:
            if question.scq_correct_options is not None and question.scq_options:
                try:
                    return [question.scq_options[question.scq_correct_options]]
                except (IndexError, TypeError):
                    return None
        return None

    def _check_answer(self, question: Question, user_answer: List[str]) -> bool:
        """Check if the user's answer is correct"""
        if question.type == QuestionType.INTEGER:
            if question.integer_answer is None:
                return False
            try:
                return int(user_answer[0]) == question.integer_answer
            except (ValueError, IndexError):
                return False
        
        elif question.type == QuestionType.MCQ:
            if not question.mcq_correct_option or not question.mcq_options:
                return False
            try:
                correct_answers = set(question.mcq_options[idx] for idx in question.mcq_correct_option)
            except (IndexError, TypeError):
                return False

            user_answers_normalized = set()
            for ans in user_answer:
                try:
                    ans_idx = int(ans)
                    if 0 <= ans_idx < len(question.mcq_options):
                        user_answers_normalized.add(question.mcq_options[ans_idx])
                        continue
                except (ValueError, TypeError):
                    pass
                user_answers_normalized.add(ans)

            return correct_answers == user_answers_normalized
        
        elif question.type == QuestionType.SCQ:
            if question.scq_correct_options is None or not question.scq_options:
                return False
            try:
                correct_answer = question.scq_options[question.scq_correct_options]
            except (IndexError, TypeError):
                return False

            if not user_answer:
                return False

            submission = user_answer[0]
            if submission == correct_answer:
                return True
            try:
                return int(submission) == question.scq_correct_options
            except (ValueError, TypeError):
                return False
        
        return False

    # ==================== Analysis Methods ====================

    async def get_analysis_by_id(self, analysis_id: UUID) -> Optional[CustomTestAnalysis]:
        """Get a custom test analysis by ID"""
        return await get_analysis_by_id(self.db, analysis_id)


    async def delete_analysis(self, analysis_id: UUID, user_id: UUID) -> bool:
        """Delete a custom test analysis"""
        analysis = await self.get_analysis_by_id(analysis_id)
        if not analysis:
            return False
        
        # Verify ownership
        if analysis.user_id != user_id:
            return False
        
        return await delete_analysis(self.db, analysis_id)

    # ==================== Statistics ====================

    async def get_user_stats(self, user_id: UUID) -> dict:
        """Get custom test statistics for a user"""
        return await get_user_test_stats(self.db, user_id)

