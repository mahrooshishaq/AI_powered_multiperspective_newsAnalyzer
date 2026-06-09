import os
import hashlib
from newsapi import NewsApiClient
from config.settings import NEWS_SOURCES, NEWS_SOURCE_DOMAINS
from utils.logger import get_logger
from utils.text_cleaner import clean_text

logger = get_logger(__name__)

SOURCE_DOMAIN_MAP = NEWS_SOURCE_DOMAINS
DOMAIN_TO_SOURCE = {v: k for k, v in SOURCE_DOMAIN_MAP.items()}


def _get_client():
    key = os.getenv("NEWSAPI_KEY", "")
    if not key or key == "your_newsapi_org_key_here":
        return None
    return NewsApiClient(api_key=key)


def fetch_articles(query: str, sources: list = None) -> list:
    client = _get_client()
    if client is None:
        logger.warning("NewsAPI key not configured. Skipping live fetch.")
        return []

    targets = sources if sources else NEWS_SOURCES
    all_articles = []

    for source_name in targets:
        domain = SOURCE_DOMAIN_MAP.get(source_name)
        if not domain:
            continue
        try:
            response = client.get_everything(
                q=query,
                domains=domain,
                language="en",
                sort_by="publishedAt",
                page_size=5,
            )
            raw_articles = response.get("articles", [])
            for a in raw_articles:
                title = a.get("title", "") or ""
                description = a.get("description", "") or ""
                content = a.get("content", "") or ""
                combined = clean_text(f"{title}. {description} {content}")
                url = a.get("url", "") or ""
                pub_at = a.get("publishedAt", "") or ""

                doc_id = hashlib.md5(url.encode()).hexdigest() if url else hashlib.md5(combined[:100].encode()).hexdigest()

                all_articles.append({
                    "id": doc_id,
                    "text": combined,
                    "source": source_name,
                    "title": title,
                    "url": url,
                    "published_at": pub_at,
                })
            logger.info(f"NewsAPI: fetched {len(raw_articles)} articles for {source_name}.")
        except Exception as e:
            logger.warning(f"NewsAPI fetch failed for {source_name}: {e}")

    all_articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return all_articles
