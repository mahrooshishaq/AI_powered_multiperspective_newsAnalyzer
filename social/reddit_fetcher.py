import os
import praw
from config.settings import REDDIT_POST_LIMIT, REDDIT_COMMENT_LIMIT
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_reddit():
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    user_agent = os.getenv("REDDIT_USER_AGENT", "news_analyzer:v1.0")

    if not client_id or client_id == "your_reddit_app_client_id":
        return None
    if not client_secret or client_secret == "your_reddit_app_client_secret":
        return None

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        check_for_async=False,
    )


def fetch_posts(query: str) -> list:
    reddit = _get_reddit()
    if reddit is None:
        logger.warning("Reddit credentials not configured. Skipping Reddit fetch.")
        return []

    posts = []
    subreddits = ["worldnews", "news", "geopolitics"]

    for sub_name in subreddits:
        try:
            sub = reddit.subreddit(sub_name)
            results = sub.search(
                query,
                limit=REDDIT_POST_LIMIT,
                sort="relevance",
                time_filter="month",
            )
            for submission in results:
                comments = []
                try:
                    submission.comments.replace_more(limit=0)
                    for comment in submission.comments[:REDDIT_COMMENT_LIMIT * 2]:
                        body = getattr(comment, "body", "")
                        author = getattr(comment, "author", None)
                        author_name = str(author) if author else ""
                        if (
                            body
                            and body not in ("[deleted]", "[removed]")
                            and author_name.lower() != "automoderator"
                        ):
                            comments.append(body[:300])
                            if len(comments) >= REDDIT_COMMENT_LIMIT:
                                break
                except Exception as ce:
                    logger.warning(f"Could not fetch comments for post '{submission.title}': {ce}")

                posts.append({
                    "title": submission.title,
                    "score": submission.score,
                    "url": submission.url,
                    "subreddit": sub_name,
                    "comments": comments,
                })

            logger.info(f"Reddit r/{sub_name}: fetched {len(posts)} posts total so far.")
        except Exception as e:
            logger.warning(f"Reddit search failed for r/{sub_name}: {e}")

    return posts
