"""
UGC Aggregation Pipeline — replaces the single Reddit dependency.

Sources:
  1. Hacker News  — free, no auth, always active
  2. YouTube      — free tier (10k units/day), needs YOUTUBE_API_KEY

All sources are normalised to the same dict structure so the
prompt_builder and UI components work without changes.

After aggregation, posts are filtered by embedding similarity to the
query — irrelevant results (below UGC_RELEVANCE_THRESHOLD) are dropped.
"""
from config.settings import UGC_RELEVANCE_THRESHOLD
from utils.logger import get_logger

logger = get_logger(__name__)


def _filter_relevant_ugc(query_embedding: list, posts: list) -> list:
    """
    Keep only posts whose title is semantically close to the query.
    Uses dot product as cosine similarity (embeddings are L2-normalised).
    Returns empty list if fewer than 2 posts survive, so the UI shows
    'No relevant public opinion found' rather than off-topic content.
    """
    from retrieval.embedder import embed_text

    surviving = []
    for post in posts:
        title = (post.get("title") or "").strip()
        if not title:
            continue
        try:
            emb = embed_text(title)
            sim = sum(a * b for a, b in zip(query_embedding, emb))
            if sim >= UGC_RELEVANCE_THRESHOLD:
                surviving.append(post)
                logger.debug(f"UGC kept   (sim={sim:.3f}): {title[:60]}")
            else:
                logger.debug(f"UGC dropped (sim={sim:.3f}): {title[:60]}")
        except Exception as e:
            logger.warning(f"Could not embed UGC title '{title[:40]}': {e}")
            surviving.append(post)  # fail-open: keep post on embedding error

    if len(surviving) < 2:
        logger.info(
            f"UGC filter: only {len(surviving)} post(s) passed threshold "
            f"{UGC_RELEVANCE_THRESHOLD} — returning empty list."
        )
        return []

    logger.info(
        f"UGC filter: {len(surviving)}/{len(posts)} posts passed "
        f"relevance threshold {UGC_RELEVANCE_THRESHOLD}."
    )
    return surviving


def fetch_ugc(query: str) -> list:
    posts = []

    # 1 — Hacker News (always attempted, no key needed)
    try:
        from social.hackernews_fetcher import fetch_posts as hn_fetch
        hn_posts = hn_fetch(query, limit=8)
        posts.extend(hn_posts)
        logger.info(f"UGC pipeline — Hacker News: {len(hn_posts)} posts.")
    except Exception as e:
        logger.warning(f"Hacker News fetch error: {e}")

    # 2 — YouTube (only if API key is set)
    try:
        from social.youtube_fetcher import fetch_posts as yt_fetch
        yt_posts = yt_fetch(query, max_videos=3, max_comments=5)
        posts.extend(yt_posts)
        logger.info(f"UGC pipeline — YouTube: {len(yt_posts)} videos.")
    except Exception as e:
        logger.warning(f"YouTube fetch error: {e}")

    logger.info(f"UGC pipeline total before filter: {len(posts)} items for '{query}'.")

    # 3 — Relevance filter via embedding similarity
    if posts:
        try:
            from retrieval.embedder import embed_text
            q_emb = embed_text(query)
            posts = _filter_relevant_ugc(q_emb, posts)
        except Exception as e:
            logger.warning(f"UGC relevance filter failed: {e}. Returning unfiltered posts.")

    logger.info(f"UGC pipeline total after filter: {len(posts)} items for '{query}'.")
    return posts
