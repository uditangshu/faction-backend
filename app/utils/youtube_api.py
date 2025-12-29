"""YouTube API utility for fetching video metadata"""

import re
import httpx
from typing import Optional
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class YouTubeVideoMetadata:
    """YouTube video metadata"""
    video_id: str
    title: str
    description: str
    thumbnail_url: str
    duration_seconds: int


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/watch\?.*v=)([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Check if the URL is just the video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    
    return None


def parse_duration(duration: str) -> int:
    """
    Parse ISO 8601 duration format (PT1H2M3S) to seconds
    """
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds


async def fetch_youtube_metadata(video_id: str) -> Optional[YouTubeVideoMetadata]:
    """
    Fetch video metadata from YouTube Data API
    
    Requires YOUTUBE_API_KEY in settings
    """
    api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    
    if not api_key:
        print("WARNING: YOUTUBE_API_KEY not configured, skipping metadata fetch")
        return None
    
    url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?id={video_id}"
        f"&part=snippet,contentDetails"
        f"&key={api_key}"
    )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        
        items = data.get("items", [])
        if not items:
            return None
        
        video = items[0]
        snippet = video.get("snippet", {})
        content_details = video.get("contentDetails", {})
        
        # Get best thumbnail (maxres > high > medium > default)
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("maxres", {}).get("url") or
            thumbnails.get("high", {}).get("url") or
            thumbnails.get("medium", {}).get("url") or
            thumbnails.get("default", {}).get("url") or
            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        )
        
        return YouTubeVideoMetadata(
            video_id=video_id,
            title=snippet.get("title", ""),
            description=snippet.get("description", ""),
            thumbnail_url=thumbnail_url,
            duration_seconds=parse_duration(content_details.get("duration", "PT0S")),
        )
    
    except Exception as e:
        print(f"Error fetching YouTube metadata: {e}")
        return None


async def get_metadata_from_url(youtube_url: str) -> Optional[YouTubeVideoMetadata]:
    """
    Get YouTube video metadata from URL
    
    Returns None if video ID cannot be extracted or API call fails
    """
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return None
    
    return await fetch_youtube_metadata(video_id)
