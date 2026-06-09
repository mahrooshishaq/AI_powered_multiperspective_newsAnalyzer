"""
Hacker News public opinion fetcher via the Algolia HN Search API.
Completely free — no API key required.
"""
import requests
from utils.logger import get_logger

logger = get_logger(__name__)

ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"
ALGOLIA_ITEM = "https://hn.algolia.com/api/v1/items/{}"
TIMEOUT = 8


def fetch_posts(query: str, limit: int = 8) -> list:
    try:
        resp = requests.get(
            ALGOLIA_SEARCH,
            params={
                "query": query,
                "tags": "story",
                "hitsPerPage": limit,
                "numericFilters": "points>5",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except Exception as e:
        logger.warning(f"Hacker News search failed: {e}")
        return []

    posts = []
    for hit in hits:
        object_id = hit.get("objectID", "")
        title = hit.get("title", "") or ""
        score = hit.get("points", 0) or 0
        url = hit.get("url", "") or f"https://news.ycombinator.com/item?id={object_id}"
        comments = _fetch_top_comments(object_id, max_comments=5)

        posts.append({
            "platform": "Hacker News",
            "title": title,
            "score": score,
            "url": url,
            "subreddit": "Hacker News",
            "comments": comments,
        })

    logger.info(f"Hacker News: fetched {len(posts)} posts for '{query}'.")
    return posts


def _fetch_top_comments(object_id: str, max_comments: int = 5) -> list:
    if not object_id:
        return []
    try:
        resp = requests.get(
            ALGOLIA_ITEM.format(object_id),
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        children = data.get("children", [])
        comments = []
        for child in children:
            text = child.get("text", "") or ""
            if text and text.strip() and len(comments) < max_comments:
                # Strip HTML tags crudely
                import re
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                comments.append(text[:300])
        return comments
    except Exception:
        return []
