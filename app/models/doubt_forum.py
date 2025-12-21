"""Doubt forum models"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from typing import List, Optional


class DoubtPost(SQLModel, table=True):
    """Doubt post model"""
    
    __tablename__ = "doubt_posts"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    class_id: UUID = Field(foreign_key="class.id", index=True)
    
    # Post content
    title: str = Field(max_length=200)
    content: str
    image_url: Optional[str] = Field(default=None, max_length=500)
    
    # Status
    is_solved: bool = Field(default=False, index=True)
    likes_count: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    comments: List["DoubtComment"] = Relationship(back_populates="post")



class DoubtComment(SQLModel, table=True):
    """Comment model for doubt posts"""
    
    __tablename__ = "doubt_comments"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    post_id: UUID = Field(foreign_key="doubt_posts.id", index=True)
    
    content: str
    image_url: Optional[str] = Field(default=None, max_length=500)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    post: Optional[DoubtPost] = Relationship(back_populates="comments")


class DoubtBookmark(SQLModel, table=True):
    """User bookmarked doubt post"""
    
    __tablename__ = "doubt_bookmarks"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    post_id: UUID = Field(foreign_key="doubt_posts.id", index=True)
    
    created_at: datetime = Field(default_factory=datetime.now, index=True)

