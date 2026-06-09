import hashlib
import os
import chromadb
from config.settings import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, NEWS_SOURCES
from utils.logger import get_logger

logger = get_logger(__name__)

_client = None
_collection = None


def _get_client():
    global _client
    if _client is None:
        # Resolve relative path against the app root (news_analyzer/)
        db_path = CHROMA_PERSIST_DIR if os.path.isabs(CHROMA_PERSIST_DIR) else os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), CHROMA_PERSIST_DIR
        )
        os.makedirs(db_path, exist_ok=True)
        _client = chromadb.PersistentClient(path=db_path)
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )
        logger.info(f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' ready. "
                    f"Documents: {_collection.count()}")
    return _collection


def _make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def add_articles(articles: list):
    collection = get_collection()
    ids, embeddings, documents, metadatas = [], [], [], []

    for article in articles:
        doc_id = article.get("id") or _make_id(article.get("url", str(article)))
        ids.append(doc_id)
        embeddings.append(article["embedding"])
        documents.append(article["text"])
        metadatas.append({
            "source": article.get("source", ""),
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "published_at": article.get("published_at", ""),
        })

    if not ids:
        return

    existing = set(collection.get(ids=ids)["ids"])
    new_ids, new_embs, new_docs, new_metas = [], [], [], []
    for i, doc_id in enumerate(ids):
        if doc_id not in existing:
            new_ids.append(doc_id)
            new_embs.append(embeddings[i])
            new_docs.append(documents[i])
            new_metas.append(metadatas[i])

    if new_ids:
        collection.upsert(
            ids=new_ids,
            embeddings=new_embs,
            documents=new_docs,
            metadatas=new_metas,
        )
        logger.info(f"Added {len(new_ids)} new documents to ChromaDB.")
    else:
        logger.info("All articles already exist in ChromaDB — skipping.")


def search(query_embedding: list, n_results: int, source_filter: str = None) -> list:
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []

    where = {"source": source_filter} if source_filter else None
    actual_n = min(n_results, count)

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_n,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.warning(f"ChromaDB search failed: {e}")
        return []

    articles = []
    for i in range(len(results["ids"][0])):
        articles.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i].get("source", ""),
            "title": results["metadatas"][0][i].get("title", ""),
            "url": results["metadatas"][0][i].get("url", ""),
            "published_at": results["metadatas"][0][i].get("published_at", ""),
            "distance": results["distances"][0][i],
        })
    return articles


def search_per_source(query_embedding: list, n_per_source: int) -> list:
    all_results = []
    for source in NEWS_SOURCES:
        results = search(query_embedding, n_results=n_per_source, source_filter=source)
        all_results.extend(results)
    return all_results


def get_collection_count() -> int:
    try:
        return get_collection().count()
    except Exception as e:
        logger.warning(f"Could not get collection count: {e}")
        return 0


def clear_collection():
    global _collection
    client = _get_client()
    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
        logger.info(f"Collection '{CHROMA_COLLECTION_NAME}' deleted.")
    except Exception:
        pass
    _collection = client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )
    logger.info(f"Collection '{CHROMA_COLLECTION_NAME}' recreated.")
