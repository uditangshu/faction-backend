"""Contest endpoints"""

from fastapi import APIRouter, Query

from uuid import UUID
from app.api.v1.dependencies import ContestServiceDep, CurrentUser
from app.schemas.contest import (
    ContestCreateRequest, 
    ContestResponse, 
    ContestListResponse,
    ContestQuestionsResponse,
    ContestQuestionResponse,
    ContestSubmissionRequest,
    ContestSubmissionResponse,
    ContestLeaderboardResponse,
)
from app.exceptions.http_exceptions import BadRequestException, NotFoundException

router = APIRouter(prefix="/contests", tags=["Contests"])


@router.post("/", response_model=ContestResponse, status_code=201)
async def create_contest(
    contest_service: ContestServiceDep,
    request: ContestCreateRequest,
) -> ContestResponse:
    """
    Create a contest with questions.
    
    Takes an array of question IDs and creates a contest with those questions.
    The contest and contest linking models are populated with UUID mappings.
    """
    try:
        contest = await contest_service.create_contest(
            name=request.name,
            description=request.description,
            question_ids=request.question_ids,
            total_time=request.total_time,
            status=request.status,
            starts_at=request.starts_at,
            ends_at=request.ends_at,
        )
        return ContestResponse.model_validate(contest)
    except (BadRequestException, NotFoundException):
        # Let HTTPException subclasses propagate
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create contest: {str(e)}")


@router.get("/", response_model=ContestListResponse)
async def get_contests(
    contest_service: ContestServiceDep,
    current_user: CurrentUser,
    type: str = Query(..., description="Type of contests: 'upcoming' or 'past'"),
) -> ContestListResponse:
    """
    Get contests by type with has_attempted status for current user.
    
    Fetches either upcoming contests (contests that haven't started yet) 
    or past contests (contests that have ended). Each contest includes
    has_attempted flag indicating if current user has already submitted.
    
    - type='upcoming': Returns contests that haven't started yet, ordered by start time (ascending)
    - type='past': Returns contests that have ended, ordered by end time (descending)
    """
    try:
        if type.lower() == "upcoming":
            contests = await contest_service.get_upcoming_contests()
        elif type.lower() == "past":
            contests = await contest_service.get_past_contests()
        else:
            raise BadRequestException("Type must be either 'upcoming' or 'past'")
        
        # Check has_attempted for each contest
        contest_responses = []
        for contest in contests:
            has_attempted = await contest_service.check_user_has_attempted(
                contest_id=contest.id,
                user_id=current_user.id,
            )
            response = ContestResponse.model_validate(contest)
            response.has_attempted = has_attempted
            contest_responses.append(response)
        
        return ContestListResponse(contests=contest_responses)
    except (BadRequestException, NotFoundException):
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to fetch contests: {str(e)}")


@router.get("/{contest_id}/questions", response_model=ContestQuestionsResponse)
async def get_contest_questions(
    contest_id: UUID,
    contest_service: ContestServiceDep,
) -> ContestQuestionsResponse:
    """
    Get contest questions with full details including subject info.
    
    Fetches all questions for a contest with complete details including subject_id and subject_name.
    Results are cached in Redis for improved performance.
    On subsequent requests, data is served from cache if available.
    """
    try:
        questions_data = await contest_service.get_contest_questions_with_details(contest_id)
        
        # Convert dictionary data to response models
        question_responses = []
        for q_data in questions_data:
            from app.models.Basequestion import QuestionType, DifficultyLevel
            from app.models.user import TargetExam
            
            question_responses.append(
                ContestQuestionResponse(
                    id=UUID(q_data["id"]),
                    topic_id=UUID(q_data["topic_id"]),
                    subject_id=UUID(q_data["subject_id"]) if q_data.get("subject_id") else None,
                    subject_name=q_data.get("subject_name"),
                    type=QuestionType(q_data["type"]),
                    difficulty=DifficultyLevel(q_data["difficulty"]),
                    exam_type=[TargetExam(exam) for exam in q_data["exam_type"]],
                    question_text=q_data["question_text"],
                    marks=q_data["marks"],
                    solution_text=q_data["solution_text"],
                    question_image=q_data.get("question_image"),
                    integer_answer=q_data.get("integer_answer"),
                    mcq_options=q_data.get("mcq_options"),
                    mcq_correct_option=q_data.get("mcq_correct_option"),
                    scq_options=q_data.get("scq_options"),
                    scq_correct_options=q_data.get("scq_correct_options"),
                    questions_solved=q_data["questions_solved"],
                )
            )
        
        return ContestQuestionsResponse(questions=question_responses)
    except (BadRequestException, NotFoundException):
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to fetch contest questions: {str(e)}")


@router.post("/submit", response_model=ContestSubmissionResponse, status_code=202)
async def submit_contest(
    contest_service: ContestServiceDep,
    current_user: CurrentUser,
    request: ContestSubmissionRequest,
) -> ContestSubmissionResponse:
    """
    Submit contest answers.
    
    Accepts an array of submission attempts and pushes them to a Redis queue
    for asynchronous processing. This allows for fast response times while
    processing submissions in the background.
    
    The submissions are queued with the format:
    - contest_id: Contest ID
    - user_id: User ID (from authenticated user)
    - question_id: Question ID
    - user_answer: List of user's answers
    - is_correct: Whether the answer is correct
    - marks_obtained: Marks obtained for this attempt
    - time_taken: Time taken in seconds
    - hint_used: Whether hint was used
    """
    try:
        # Convert submission attempts to dictionaries
        submissions_data = []
        for submission in request.submissions:
            submissions_data.append({
                "question_id": submission.question_id,
                "user_answer": submission.user_answer,
                "time_taken": submission.time_taken,
                "hint_used": submission.hint_used,
            })
        
        # Push all submissions to Redis queue
        queue_name = await contest_service.push_submissions_to_queue(
            contest_id=request.contest_id,
            user_id=current_user.id,
            submissions=submissions_data,
        )
        
        return ContestSubmissionResponse(
            message="Submissions queued successfully",
            submissions_count=len(request.submissions),
            queue_name=queue_name,
        )
    except (BadRequestException, NotFoundException):
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to submit contest: {str(e)}")


@router.get("/{contest_id}/leaderboard/{user_id}", response_model=ContestLeaderboardResponse)
async def get_contest_leaderboard(
    contest_id: UUID,
    user_id: UUID,
    contest_service: ContestServiceDep,
) -> ContestLeaderboardResponse:
    """
    Get contest leaderboard entry for a specific user and contest.
    
    Returns the leaderboard entry containing:
    - Score and rank
    - Rating information (before, after, delta)
    - Submission analytics (accuracy, attempted, correct, incorrect, etc.)
    
    Raises NotFoundException if the contest or leaderboard entry doesn't exist.
    """
    try:
        leaderboard_entry = await contest_service.get_contest_leaderboard(
            contest_id=contest_id,
            user_id=user_id,
        )
        
        return ContestLeaderboardResponse.model_validate(leaderboard_entry)
    except (BadRequestException, NotFoundException):
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to fetch contest leaderboard: {str(e)}")


@router.get("/{contest_id}/has-attempted", response_model=dict)
async def check_has_attempted(
    contest_id: UUID,
    current_user: CurrentUser,
    contest_service: ContestServiceDep,
) -> dict:
    """
    Check if the current user has already attempted this contest.
    
    Returns:
    - has_attempted: boolean indicating if user has submitted to this contest
    - Can be used to prevent re-attempts
    """
    try:
        has_attempted = await contest_service.check_user_has_attempted(
            contest_id=contest_id,
            user_id=current_user.id,
        )
        return {"has_attempted": has_attempted}
    except Exception as e:
        raise BadRequestException(f"Failed to check attempt status: {str(e)}")


