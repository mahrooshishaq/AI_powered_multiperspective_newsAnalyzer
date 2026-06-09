import os
import json
import hashlib
import time
from config.settings import CACHE_TTL_HOURS
from utils.logger import get_logger

logger = get_logger(__name__)

CACHE_DIR = "cache"


def _cache_path(query: str) -> str:
    key = hashlib.md5(query.strip().lower().encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.json")


def get_cached_result(query: str):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(query)
    if not os.path.exists(path):
        return None
    age_hours = (time.time() - os.path.getmtime(path)) / 3600
    if age_hours > CACHE_TTL_HOURS:
        logger.info(f"Cache expired for query '{query}' (age: {age_hours:.1f}h).")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        logger.info(f"Cache hit for query '{query}'.")
        return result
    except Exception as e:
        logger.warning(f"Failed to read cache file: {e}")
        return None


def save_to_cache(query: str, result: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(query)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"Cached result for query '{query}'.")
    except Exception as e:
        logger.warning(f"Failed to write cache: {e}")


def clear_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)
    deleted = 0
    for fname in os.listdir(CACHE_DIR):
        if fname.endswith(".json"):
            try:
                os.remove(os.path.join(CACHE_DIR, fname))
                deleted += 1
            except Exception as e:
                logger.warning(f"Could not delete cache file {fname}: {e}")
    logger.info(f"Cleared {deleted} cache files.")
    return deleted
