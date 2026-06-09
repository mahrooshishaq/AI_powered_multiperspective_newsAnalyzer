import streamlit as st
from utils.logger import get_logger

logger = get_logger(__name__)


@st.cache_resource(show_spinner="Loading embedding model (BAAI/bge-m3)…")
def _load_model():
    from sentence_transformers import SentenceTransformer
    try:
        model = SentenceTransformer("BAAI/bge-m3")
        logger.info("BAAI/bge-m3 embedding model loaded successfully.")
        return model
    except Exception as e:
        logger.error(
            f"Failed to load BAAI/bge-m3. Ensure internet access on first run "
            f"(model ~2.3 GB). Error: {e}"
        )
        return None


def _get_model():
    try:
        return _load_model()
    except Exception:
        # Outside Streamlit context (e.g. ingest.py CLI) — load directly
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("BAAI/bge-m3")


def embed_texts(texts: list) -> list:
    model = _get_model()
    if model is None:
        raise RuntimeError(
            "Embedding model (BAAI/bge-m3) failed to load. Check logs. "
            "If running for the first time, wait for the model to download (~2.3 GB)."
        )
    if not texts:
        return []
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]


def embed_text(text: str) -> list:
    return embed_texts([text])[0]
