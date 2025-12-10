import asyncio
from uuid import UUID, uuid4
from sqlalchemy import select
from app.core.db import AsyncSessionLocal
from app.models.Basequestion import Class, Subject, Chapter, Class_level, Subject_Type
from app.models.youtube_video import YouTubeVideo

async def seed_video():
    async with AsyncSessionLocal() as session:
        print("🌱 Seeding YouTube video...")

        # 1. Ensure Class exists (e.g., Class 11)
        stmt = select(Class).where(Class.class_level == Class_level.Eleventh)
        class_obj = (await session.execute(stmt)).scalar_one_or_none()
        
        if not class_obj:
            print("Creating Class 11...")
            class_obj = Class(class_level=Class_level.Eleventh)
            session.add(class_obj)
            await session.commit()
            await session.refresh(class_obj)
        
        # 2. Ensure Subject exists (e.g., Maths)
        stmt = select(Subject).where(
            Subject.subject_type == Subject_Type.MATHS,
            Subject.class_id == class_obj.id
        )
        subject = (await session.execute(stmt)).scalar_one_or_none()
        
        if not subject:
            print("Creating Maths Subject...")
            subject = Subject(subject_type=Subject_Type.MATHS, class_id=class_obj.id)
            session.add(subject)
            await session.commit()
            await session.refresh(subject)
            
        # 3. Ensure Chapter exists (e.g., Trigonometry)
        chapter_name = "Trigonometry"
        stmt = select(Chapter).where(
            Chapter.name == chapter_name,
            Chapter.subject_id == subject.id
        )
        chapter = (await session.execute(stmt)).scalar_one_or_none()
        
        if not chapter:
            print(f"Creating {chapter_name} Chapter...")
            chapter = Chapter(name=chapter_name, subject_id=subject.id)
            session.add(chapter)
            await session.commit()
            await session.refresh(chapter)

        # 4. Create YouTube Video
        video_title = "Introduction to Trigonometry"
        instructor_name = "Er. Soumyadeep Nandi"
        instructor_inst = "IIT KGP"
        youtube_url = "https://www.youtube.com/watch?v=PUB0TaZ7bhA"
        video_id = "PUB0TaZ7bhA"
        
        stmt = select(YouTubeVideo).where(YouTubeVideo.youtube_video_id == video_id)
        existing_video = (await session.execute(stmt)).scalar_one_or_none()
        
        if existing_video:
            print(f"Updating existing video {video_title}...")
            existing_video.title = video_title
            existing_video.instructor_name = instructor_name
            existing_video.instructor_institution = instructor_inst
            existing_video.duration_seconds = 502 # 8:22
            existing_video.chapter_id = chapter.id
            existing_video.subject_id = subject.id
            existing_video.is_active = True
            session.add(existing_video)
        else:
            print(f"Creating new video {video_title}...")
            video = YouTubeVideo(
                chapter_id=chapter.id,
                subject_id=subject.id,
                youtube_video_id=video_id,
                youtube_url=youtube_url,
                title=video_title,
                description="Introduction to Trigonometry concepts",
                thumbnail_url=f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                duration_seconds=502, # 8:22
                instructor_name=instructor_name,
                instructor_institution=instructor_inst,
                is_active=True
            )
            session.add(video)
        
        await session.commit()
        print("✅ Video seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_video())

