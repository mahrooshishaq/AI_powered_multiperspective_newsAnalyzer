"""
Run this script once to populate the ChromaDB vector database with CC-News articles.
Usage: python data/ingest.py
"""
import sys
import os
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datasets import load_dataset
from tqdm import tqdm

from config.settings import (
    CHUNK_SIZE, CHUNK_OVERLAP, NEWS_SOURCE_DOMAINS, NEWS_SOURCES
)
from retrieval.embedder import embed_texts
from retrieval.chromadb_store import get_collection_count, add_articles, get_collection
from utils.text_cleaner import clean_text
from utils.logger import get_logger

logger = get_logger(__name__)

DOMAIN_TO_SOURCE = {v: k for k, v in NEWS_SOURCE_DOMAINS.items()}
MAX_PER_SOURCE = 500


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def main():
    existing = get_collection_count()
    if existing > 0:
        answer = input(
            f"ChromaDB already has {existing} documents. Re-ingest anyway? (y/N): "
        ).strip().lower()
        if answer != "y":
            logger.info("Skipping ingestion.")
            return

    logger.info("Loading CC-News dataset in streaming mode...")
    dataset = load_dataset("cc_news", split="train", streaming=True, trust_remote_code=True)

    counts = {source: 0 for source in NEWS_SOURCES}
    total_chunks_added = 0

    pbar = tqdm(dataset, desc="Scanning CC-News")
    for article in pbar:
        domain = article.get("domain", "")
        matched_source = None
        for d, source in DOMAIN_TO_SOURCE.items():
            if d in domain:
                matched_source = source
                break

        if matched_source is None:
            continue
        if counts[matched_source] >= MAX_PER_SOURCE:
            if all(v >= MAX_PER_SOURCE for v in counts.values()):
                break
            continue

        raw_text = article.get("text", "") or ""
        title = article.get("title", "") or ""
        url = article.get("url", "") or ""
        date = article.get("published_date", "") or ""
        if isinstance(date, object) and hasattr(date, "isoformat"):
            date = date.isoformat()
        else:
            date = str(date)

        cleaned = clean_text(raw_text)
        if len(cleaned.split()) < 50:
            continue

        chunks = chunk_text(cleaned)
        article_hash = url_hash(url) if url else url_hash(title + matched_source)

        articles_to_add = []
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{article_hash}_chunk_{idx}"
            embedding = embed_texts([chunk])[0]
            articles_to_add.append({
                "id": chunk_id,
                "text": chunk,
                "embedding": embedding,
                "source": matched_source,
                "title": title,
                "url": url,
                "published_at": date,
            })

        add_articles(articles_to_add)
        counts[matched_source] += 1
        total_chunks_added += len(chunks)

        pbar.set_postfix({s[:3]: counts[s] for s in NEWS_SOURCES})

    logger.info("Ingestion complete.")
    logger.info(f"Articles ingested per source: {counts}")
    logger.info(f"Total chunks stored: {total_chunks_added}")
    logger.info(f"Total ChromaDB documents: {get_collection_count()}")


if __name__ == "__main__":
    main()
