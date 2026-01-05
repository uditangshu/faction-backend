"""
Script to import questions from JSON file into the database.

Usage:
    python import_questions.py --data questions_combined.json
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Optional, List
from uuid import UUID

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.Basequestion import (
    Class, Subject, Chapter, Topic, Question,
    Class_level, Subject_Type, QuestionType, DifficultyLevel
)
from app.models.user import TargetExam
from app.models.pyq import PreviousYearProblems


async def get_or_create_class(db: AsyncSession, name: str) -> Class:
    """Get or create a Class entry"""
    result = await db.execute(
        select(Class).where(Class.name == name)
    )
    class_obj = result.scalar_one_or_none()
    
    if not class_obj:
        class_obj = Class(name=name)
        db.add(class_obj)
        await db.flush()
    return class_obj


async def get_or_create_subject(
    db: AsyncSession,
    class_obj: Class,
    subject_type: Subject_Type,
    exam_types: List[TargetExam]
) -> Subject:
    """Get or create a Subject entry"""
    result = await db.execute(
        select(Subject).where(
            Subject.class_id == class_obj.id,
            Subject.subject_type == subject_type
        )
    )
    subject = result.scalar_one_or_none()
    
    if not subject:
        subject = Subject(
            class_id=class_obj.id,
            subject_type=subject_type,
            exam_type=exam_types
        )
        db.add(subject)
        await db.flush()
    else:
        # Update exam types if they've changed
        if set(subject.exam_type) != set(exam_types):
            subject.exam_type = exam_types
            await db.flush()
    
    return subject


async def get_or_create_chapter(
    db: AsyncSession,
    subject: Subject,
    chapter_name: str
) -> Chapter:
    """Get or create a Chapter entry"""
    result = await db.execute(
        select(Chapter).where(
            Chapter.subject_id == subject.id,
            Chapter.name == chapter_name
        )
    )
    chapter = result.scalar_one_or_none()
    
    if not chapter:
        chapter = Chapter(
            subject_id=subject.id,
            name=chapter_name
        )
        db.add(chapter)
        await db.flush()
    
    return chapter


async def get_or_create_topic(
    db: AsyncSession,
    chapter: Chapter,
    topic_name: str
) -> Topic:
    """Get or create a Topic entry"""
    result = await db.execute(
        select(Topic).where(
            Topic.chapter_id == chapter.id,
            Topic.name == topic_name
        )
    )
    topic = result.scalar_one_or_none()
    
    if not topic:
        topic = Topic(
            chapter_id=chapter.id,
            name=topic_name
        )
        db.add(topic)
        await db.flush()
    
    return topic


def parse_question_type(q_type: str) -> QuestionType:
    """Parse question type string to enum"""
    type_mapping = {
        "integer": QuestionType.INTEGER,
        "mcq": QuestionType.MCQ,
        "match_the_column": QuestionType.MATCH,
        "match": QuestionType.MATCH,
        "scq": QuestionType.SCQ,
        "numerical": QuestionType.INTEGER,  # Handle numerical as integer
    }
    return type_mapping.get(q_type.lower(), QuestionType.MCQ)


def parse_difficulty(difficulty: str | int) -> DifficultyLevel:
    """Parse difficulty string or int to enum"""
    if isinstance(difficulty, int):
        if difficulty == 1:
            return DifficultyLevel.EASY
        elif difficulty == 2:
            return DifficultyLevel.MEDIUM
        else:
            return DifficultyLevel.HARD
    
    difficulty_mapping = {
        "easy": DifficultyLevel.EASY,
        "medium": DifficultyLevel.MEDIUM,
        "hard": DifficultyLevel.HARD,
        "1": DifficultyLevel.EASY,
        "2": DifficultyLevel.MEDIUM,
        "3": DifficultyLevel.HARD,
    }
    return difficulty_mapping.get(str(difficulty).lower(), DifficultyLevel.MEDIUM)


def parse_exam_types(exam_types: List[str]) -> List[TargetExam]:
    """Parse exam type strings to enums"""
    exam_mapping = {
        "JEE_ADVANCED": TargetExam.JEE_ADVANCED,
        "JEE_MAINS": TargetExam.JEE_MAINS,
        "NEET": TargetExam.NEET,
        "OLYMPIAD": TargetExam.OLYMPIAD,
        "CBSE": TargetExam.CBSE,
    }
    return [exam_mapping.get(exam.upper(), TargetExam.JEE_MAINS) for exam in exam_types]


def parse_subject_type(subject_type_str: str) -> Subject_Type:
    """Parse subject type string to enum"""
    # Handle various formats
    subject_mapping = {
        "PHYSICS": Subject_Type.PHYSICS,
        "CHEMISTRY": Subject_Type.CHEMISTRY,
        "MATHS": Subject_Type.MATHS,
        "MATHEMATICS": Subject_Type.MATHS,  # Handle MATHEMATICS as MATHS
        "BIOLOGY": Subject_Type.BIOLOGY,
    }
    return subject_mapping.get(subject_type_str.upper(), Subject_Type.MATHS)


def parse_class_level(class_level_str: str) -> str:
    """Parse class level string to class name (number as string)"""
    class_name_map = {
        "Ninth": "9",
        "Tenth": "10",
        "Eleventh": "11",
        "Twelth": "12",
        "Twelfth": "12",  # Handle both spellings
    }
    return class_name_map.get(class_level_str, class_level_str)


async def create_question(
    db: AsyncSession,
    topic: Topic,
    question_data: Dict
) -> Question:
    """Create a Question entry from question data"""
    question_type = parse_question_type(question_data.get("type", "mcq"))
    difficulty = parse_difficulty(question_data.get("difficulty", 2))
    exam_types = parse_exam_types(question_data.get("exam_type", ["JEE_MAINS"]))
    
    question = Question(
        topic_id=topic.id,
        type=question_type,
        difficulty=difficulty,
        exam_type=exam_types,
        question_text=question_data["question_text"],
        marks=question_data.get("marks", 4),
        solution_text=question_data.get("solution_text", ""),
        question_image=question_data.get("question_image"),
        integer_answer=question_data.get("integer_answer"),
        mcq_options=question_data.get("mcq_options"),
        mcq_correct_option=question_data.get("mcq_correct_option"),
        scq_options=question_data.get("scq_options"),
        scq_correct_options=question_data.get("scq_correct_options"),
        questions_solved=0,
    )
    db.add(question)
    await db.flush()
    return question


async def create_pyq(
    db: AsyncSession,
    question: Question,
    pyq_data: Dict
) -> PreviousYearProblems:
    """Create a PYQ entry from PYQ data"""
    pyq = PreviousYearProblems(
        question_id=question.id,
        year=pyq_data.get("year", 2024),
        exam_detail=pyq_data.get("exam_detail", [])
    )
    db.add(pyq)
    await db.flush()
    return pyq


async def import_questions(data_file: Path):
    """Main function to import questions from JSON file"""
    print("📖 Reading JSON file...")
    # Read JSON data
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ Loaded {len(data)} questions from JSON")
    print("🔌 Connecting to database...")
    
    async with AsyncSessionLocal() as db:
        print("✅ Database connection established")
        try:
            created_count = 0
            pyq_count = 0
            skipped_count = 0
            
            for idx, item in enumerate(data, 1):
                try:
                    # Extract hierarchy information
                    class_level_value = item["class_level"]
                    if isinstance(class_level_value, str):
                        class_name = parse_class_level(class_level_value)
                    else:
                        class_name = str(class_level_value)
                    
                    subject_type_str = item["subject_type"]
                    subject_type = parse_subject_type(subject_type_str)
                    
                    chapter_name = item["chapter_name"]
                    topic_name = item["topic_name"]
                    exam_types = item.get("exam_types", ["JEE_MAINS"])
                    
                    # Create/get hierarchy
                    class_obj = await get_or_create_class(db, class_name)
                    subject = await get_or_create_subject(db, class_obj, subject_type, parse_exam_types(exam_types))
                    chapter = await get_or_create_chapter(db, subject, chapter_name)
                    topic = await get_or_create_topic(db, chapter, topic_name)
                    
                    # Create question
                    question = await create_question(db, topic, item["question"])
                    created_count += 1
                    
                    # Create PYQ if provided
                    if "pyq" in item and item["pyq"]:
                        await create_pyq(db, question, item["pyq"])
                        pyq_count += 1
                    
                    # Commit every 50 items for better performance
                    if created_count % 50 == 0:
                        await db.commit()
                        print(f"Processed {created_count} questions...")
                        
                except Exception as e:
                    print(f"❌ Error processing item {idx}: {str(e)}")
                    skipped_count += 1
                    continue
            
            # Final commit
            await db.commit()
            print(f"\n✅ Successfully imported {created_count} questions and {pyq_count} PYQ entries!")
            if skipped_count > 0:
                print(f"⚠️  Skipped {skipped_count} items due to errors.")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error importing questions: {str(e)}")
            import traceback
            traceback.print_exc()
            raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Import questions from JSON file into database")
    parser.add_argument(
        "--data",
        type=str,
        default="questions_combined.json",
        help="Path to JSON data file (default: questions_combined.json)"
    )
    args = parser.parse_args()
    
    data_file = Path(args.data)
    if not data_file.exists():
        print(f"❌ Error: Data file not found: {data_file}")
        print(f"Please provide a valid JSON file path.")
        sys.exit(1)
    
    print(f"📖 Reading data from: {data_file}")
    asyncio.run(import_questions(data_file))


if __name__ == "__main__":
    main()

