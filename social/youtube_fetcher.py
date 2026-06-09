"""
YouTube public opinion fetcher via the YouTube Data API v3.
Requires YOUTUBE_API_KEY in .env (free tier: 10,000 units/day).
"""
import os
import requests
from utils.logger import get_logger

logger = get_logger(__name__)

YOUTUBE_SEARCH = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_COMMENTS = "https://www.googleapis.com/youtube/v3/commentThreads"
TIMEOUT = 8


def _get_key():
    key = os.getenv("YOUTUBE_API_KEY", "")
    if not key or key.startswith("your_"):
        return None
    return key


def fetch_posts(query: str, max_videos: int = 3, max_comments: int = 5) -> list:
    key = _get_key()
    if not key:
        logger.info("YouTube API key not configured. Skipping YouTube fetch.")
        return []

    try:
        resp = requests.get(
            YOUTUBE_SEARCH,
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max_videos,
                "relevanceLanguage": "en",
                "order": "relevance",
                "key": key,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception as e:
        logger.warning(f"YouTube search failed: {e}")
        return []

    posts = []
    for item in items:
        video_id = item.get("id", {}).get("videoId", "")
        snippet = item.get("snippet", {})
        title = snippet.get("title", "")
        if not video_id:
            continue

        comments = _fetch_comments(video_id, key, max_comments)
        posts.append({
            "platform": "YouTube",
            "title": title,
            "score": 0,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "subreddit": "YouTube",
            "comments": comments,
        })

    logger.info(f"YouTube: fetched {len(posts)} videos with comments for '{query}'.")
    return posts


def _fetch_comments(video_id: str, key: str, max_comments: int) -> list:
    try:
        resp = requests.get(
            YOUTUBE_COMMENTS,
            params={
                "part": "snippet",
                "videoId": video_id,
                "maxResults": max_comments,
                "order": "relevance",
                "key": key,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        comments = []
        for item in items:
            text = (
                item.get("snippet", {})
                .get("topLevelComment", {})
                .get("snippet", {})
                .get("textDisplay", "")
            )
            if text:
                comments.append(text[:300])
        return comments
    except Exception as e:
        logger.warning(f"YouTube comments fetch failed for video {video_id}: {e}")
        return []
