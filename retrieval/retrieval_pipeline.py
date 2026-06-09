import os
from datetime import timezone
from config.settings import TOP_K_RETRIEVAL, TOP_K_AFTER_RERANK, NEWS_SOURCES, TEMPORAL_WINDOW_DAYS
from retrieval.embedder import embed_text
from retrieval.chromadb_store import search_per_source, add_articles
from retrieval.newsapi_fetcher import fetch_articles
from retrieval.reranker import rerank
from utils.logger import get_logger

logger = get_logger(__name__)


def _parse_date(date_str):
    """Parse a date string into a timezone-naive datetime, or return None."""
    if not date_str:
        return None
    try:
        from dateutil import parser as dateutil_parser
        dt = dateutil_parser.parse(str(date_str))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _pick_temporally_aligned(reranked: list, window_days: int):
    """
    Given articles sorted by rerank_score (desc), find the best subset with
    one article per source whose dates all fall within window_days of each other.

    Returns a list of selected articles (one per source), or None if no
    temporally aligned cluster covering all sources can be formed.
    """
    from datetime import timedelta

    # Pre-compute parsed dates once
    dated = [(a, _parse_date(a.get("published_at", ""))) for a in reranked]

    best_cluster = None
    best_score = float("-inf")

    for anchor_article, anchor_date in dated:
        if anchor_date is None:
            continue

        window_start = anchor_date - timedelta(days=window_days)
        window_end = anchor_date + timedelta(days=window_days)

        # For each source pick the highest-scoring article in the window
        # (reranked is desc by score so first match = best for that source)
        chosen = {}
        for article, dt in dated:
            src = article.get("source", "")
            if src in chosen or dt is None:
                continue
            if window_start <= dt <= window_end:
                chosen[src] = article

        if set(chosen.keys()) == set(NEWS_SOURCES):
            cluster_score = sum(a.get("rerank_score", 0.0) for a in chosen.values())
            if cluster_score > best_score:
                best_score = cluster_score
                best_cluster = list(chosen.values())

    return best_cluster  # None when no valid cluster found


def retrieve_articles(query: str, use_live_fetch: bool = True) -> tuple:
    query_embedding = embed_text(query)

    n_per_source = max(1, TOP_K_RETRIEVAL // len(NEWS_SOURCES))
    candidates = search_per_source(query_embedding, n_per_source=n_per_source)
    logger.info(f"ChromaDB returned {len(candidates)} candidates.")

    live_fetch_used = False
    newsapi_key = os.getenv("NEWSAPI_KEY", "")
    if use_live_fetch and newsapi_key and newsapi_key != "your_newsapi_org_key_here":
        live_articles = fetch_articles(query)
        if live_articles:
            live_fetch_used = True
            for article in live_articles:
                article["embedding"] = embed_text(article["text"])
            add_articles(live_articles)
            existing_urls = {a.get("url") for a in candidates}
            for article in live_articles:
                if article.get("url") not in existing_urls:
                    candidates.append(article)
            logger.info(f"Added {len(live_articles)} live articles to candidate pool.")

    seen_urls = set()
    deduplicated = []
    for article in candidates:
        url = article.get("url", "") or article.get("id", "")
        if url not in seen_urls:
            seen_urls.add(url)
            deduplicated.append(article)

    logger.info(f"Candidate pool after dedup: {len(deduplicated)}")

    if not deduplicated:
        return [], {
            "live_fetch_used": live_fetch_used,
            "articles_per_source": {s: 0 for s in NEWS_SOURCES},
            "temporal_aligned": False,
            "temporal_warning": True,
            "date_range_days": 0,
        }

    reranked = rerank(query, deduplicated, top_k=len(deduplicated))

    # --- Temporal alignment ---
    temporal_aligned = False
    temporal_warning = False
    date_range_days = 0

    aligned = _pick_temporally_aligned(reranked, window_days=TEMPORAL_WINDOW_DAYS)

    if aligned:
        final = aligned
        temporal_aligned = True
        dates = [_parse_date(a.get("published_at", "")) for a in final]
        dates = [d for d in dates if d]
        if len(dates) >= 2:
            date_range_days = (max(dates) - min(dates)).days
        logger.info(
            f"Temporal alignment succeeded. "
            f"date_range_days={date_range_days} | articles: "
            + ", ".join(f"{a.get('source')} ({a.get('published_at','?')[:10]})" for a in final)
        )
    else:
        # Fallback: original best-per-source logic
        temporal_warning = True
        logger.info(
            f"No temporally aligned cluster found within {TEMPORAL_WINDOW_DAYS} days "
            "— using best-per-source fallback."
        )
        sources_in_top = set()
        final = []
        for article in reranked:
            if len(final) >= TOP_K_AFTER_RERANK:
                break
            src = article.get("source", "")
            count_this_source = sum(1 for a in final if a.get("source") == src)
            max_per_source = max(1, TOP_K_AFTER_RERANK // len(NEWS_SOURCES))
            if count_this_source < max_per_source:
                final.append(article)
                sources_in_top.add(src)

        missing_sources = [s for s in NEWS_SOURCES if s not in sources_in_top]
        for src in missing_sources:
            source_candidates = [a for a in reranked if a.get("source") == src]
            if source_candidates:
                final.append(source_candidates[0])
                logger.info(f"Added fallback article for source: {src}")

        # Compute date range even in fallback so prompt gets temporal note
        fallback_dates = [_parse_date(a.get("published_at", "")) for a in final]
        fallback_dates = [d for d in fallback_dates if d]
        if len(fallback_dates) >= 2:
            date_range_days = (max(fallback_dates) - min(fallback_dates)).days

    articles_per_source = {
        src: sum(1 for a in final if a.get("source") == src)
        for src in NEWS_SOURCES
    }
    metadata = {
        "live_fetch_used": live_fetch_used,
        "articles_per_source": articles_per_source,
        "temporal_aligned": temporal_aligned,
        "temporal_warning": temporal_warning,
        "date_range_days": date_range_days,
    }

    logger.info(
        f"Final articles: {len(final)} | Per source: {articles_per_source} | "
        f"temporal_aligned={temporal_aligned} | date_range_days={date_range_days}"
    )
    return final, metadata
