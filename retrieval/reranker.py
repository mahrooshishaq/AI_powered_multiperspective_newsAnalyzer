import streamlit as st
from config.settings import RERANKER_MODEL_NAME
from utils.logger import get_logger

logger = get_logger(__name__)


@st.cache_resource(show_spinner="Loading reranker model…")
def _load_reranker():
    from sentence_transformers import CrossEncoder
    try:
        model = CrossEncoder(RERANKER_MODEL_NAME, max_length=512)
        logger.info(f"Reranker model '{RERANKER_MODEL_NAME}' loaded successfully.")
        return model
    except Exception as e:
        logger.error(f"Failed to load reranker model: {e}")
        return None


def _get_reranker():
    try:
        return _load_reranker()
    except Exception:
        from sentence_transformers import CrossEncoder
        return CrossEncoder(RERANKER_MODEL_NAME, max_length=512)


def rerank(query: str, articles: list, top_k: int) -> list:
    if not articles:
        return []

    reranker = _get_reranker()
    if reranker is None:
        logger.warning("Reranker not available. Returning articles as-is.")
        for a in articles:
            a["rerank_score"] = 0.0
        return articles[:top_k]

    pairs = [(query, a.get("text", "")[:1000]) for a in articles]
    try:
        scores = reranker.predict(pairs)
    except Exception as e:
        logger.warning(f"Reranker prediction failed: {e}")
        for a in articles:
            a["rerank_score"] = 0.0
        return articles[:top_k]

    for article, score in zip(articles, scores):
        article["rerank_score"] = float(score)

    sorted_articles = sorted(articles, key=lambda x: x["rerank_score"], reverse=True)
    return sorted_articles[:top_k]
