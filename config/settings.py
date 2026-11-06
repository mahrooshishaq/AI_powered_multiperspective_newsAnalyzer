CHROMA_PERSIST_DIR = "chroma_db"
CHROMA_COLLECTION_NAME = "news_articles"

EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

GROQ_MODEL_NAME = "openai/gpt-oss-120b"
GEMINI_MODEL_NAME = "gemini-2.0-flash"

TOP_K_RETRIEVAL = 15
TOP_K_AFTER_RERANK = 6

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80

NEWS_SOURCES = ["BBC News", "CNN", "Al Jazeera"]
NEWS_SOURCE_DOMAINS = {
    "BBC News": "bbc.com",
    "CNN": "cnn.com",
    "Al Jazeera": "aljazeera.com",
}

CACHE_TTL_HOURS = 24
MAX_ARTICLE_WORDS = 800

REDDIT_POST_LIMIT = 10
REDDIT_COMMENT_LIMIT = 5

TEMPORAL_WINDOW_DAYS = 7       # Max days between articles for temporal alignment
UGC_RELEVANCE_THRESHOLD = 0.45  # Min cosine similarity for UGC post to be kept
