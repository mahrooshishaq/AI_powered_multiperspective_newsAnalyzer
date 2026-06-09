import json
from datetime import datetime
from utils.logger import get_logger
from retrieval.retrieval_pipeline import retrieve_articles
from analysis.prompt_builder import build_analysis_prompt
from analysis.llm_client import call_llm, LLMUnavailableError, SYSTEM_MESSAGE

logger = get_logger(__name__)


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in LLM response.")
    return json.loads(text[start:end])


def analyze_topic(query: str, use_live_fetch: bool = True, include_ugc: bool = True) -> dict:
    logger.info(f"Starting analysis for query: '{query}'")

    articles, retrieval_meta = retrieve_articles(query, use_live_fetch=use_live_fetch)

    if not articles:
        return {
            "error": "no_articles",
            "message": (
                "No articles found for this topic. "
                "Try a broader search term or enable live fetching."
            ),
            "query": query,
        }

    ugc_posts = []
    if include_ugc:
        try:
            from social.ugc_pipeline import fetch_ugc
            ugc_posts = fetch_ugc(query)
            logger.info(f"UGC pipeline: fetched {len(ugc_posts)} posts.")
        except Exception as e:
            logger.warning(f"UGC fetch failed: {e}. Continuing without public opinion data.")

    date_range_days = retrieval_meta.get("date_range_days", 0)
    prompt = build_analysis_prompt(
        query,
        articles,
        ugc_posts if ugc_posts else None,
        date_range_days=date_range_days,
    )

    result = None
    try:
        raw_response = call_llm(prompt, system_message=SYSTEM_MESSAGE)
        result = _extract_json(raw_response)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"JSON parse failed on first attempt: {e}. Retrying.")
        retry_prompt = (
            prompt
            + "\n\nIMPORTANT: Return ONLY valid JSON, starting with { and ending with }. "
            "No markdown. No explanation. No text outside the JSON."
        )
        try:
            raw_response = call_llm(retry_prompt, system_message=SYSTEM_MESSAGE)
            result = _extract_json(raw_response)
        except Exception as e2:
            logger.error(f"JSON parse failed on retry: {e2}")
            raise RuntimeError(f"LLM returned invalid JSON after retry: {e2}")
    except LLMUnavailableError:
        raise

    result["query"] = query
    result["articles_used"] = [
        {
            "source": a.get("source", ""),
            "title": a.get("title", ""),
            "url": a.get("url", ""),
        }
        for a in articles
    ]
    result["live_fetch_used"] = retrieval_meta.get("live_fetch_used", False)
    result["articles_per_source"] = retrieval_meta.get("articles_per_source", {})
    result["ugc_posts_count"] = len(ugc_posts)
    result["ugc_posts"] = ugc_posts
    result["temporal_aligned"] = retrieval_meta.get("temporal_aligned", False)
    result["temporal_warning"] = retrieval_meta.get("temporal_warning", False)
    result["date_range_days"] = retrieval_meta.get("date_range_days", 0)
    result["timestamp"] = datetime.utcnow().isoformat()

    logger.info("Analysis complete.")
    return result
