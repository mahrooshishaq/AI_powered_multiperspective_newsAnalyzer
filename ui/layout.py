import traceback
import streamlit as st
from ui.components import (
    render_sentiment_card,
    render_framing_card,
    render_word_choice_table,
    render_omissions_section,
    render_agreements_disagreements,
    render_framing_differences,
    render_balanced_summary,
    render_public_opinion,
    render_bias_verdict,
    render_article_sources,
    render_loading_state,
)
from retrieval.chromadb_store import get_collection_count
from utils.cache import clear_cache, get_cached_result, save_to_cache
from config.settings import NEWS_SOURCES


def _render_sidebar():
    with st.sidebar:
        st.header("About")
        st.write(
            "This tool retrieves news articles from BBC News, CNN, and Al Jazeera, "
            "then uses a large language model to compare how each outlet frames the same story."
        )

        st.divider()
        st.header("Database Status")
        try:
            count = get_collection_count()
            st.metric("Articles in ChromaDB", count)
            if count == 0:
                st.caption(
                    "Database is empty. Enable 'Include live articles' to use NewsAPI, "
                    "or run `python data/ingest.py` to populate from CC-News."
                )
        except Exception:
            st.warning("Could not connect to ChromaDB.")

        st.divider()
        st.header("How It Works")
        st.markdown(
            """
1. Your query is embedded with BAAI/bge-m3
2. ChromaDB searches relevant article chunks per source
3. (Optional) NewsAPI fetches live articles
4. A cross-encoder reranker selects the best articles
5. LLaMA 3.3 70B analyzes articles and returns structured JSON
"""
        )

        st.divider()
        if st.button("Clear Cache", use_container_width=True):
            n = clear_cache()
            st.success(f"Cleared {n} cached result(s).")

        st.divider()
        if st.button("Reload Database", use_container_width=True):
            confirm = st.checkbox(
                "I understand this will re-run ingestion and may take a long time."
            )
            if confirm:
                import subprocess, sys
                with st.spinner("Running ingestion script..."):
                    result = subprocess.run(
                        [sys.executable, "data/ingest.py"],
                        capture_output=True,
                        text=True,
                    )
                if result.returncode == 0:
                    st.success("Database reloaded successfully.")
                else:
                    st.error(f"Ingestion failed:\n{result.stderr[:500]}")


def _render_results(result: dict):
    sentiment = result.get("sentiment", {})
    framing = result.get("framing", {})
    word_choice = result.get("word_choice", [])
    omissions = result.get("omissions", {})
    agreements = result.get("agreements", [])
    disagreements = result.get("disagreements", [])
    framing_diffs = result.get("framing_differences", [])
    balanced_summary = result.get("balanced_summary", "")
    public_opinion_summary = result.get("public_opinion_summary", "")
    bias_verdict = result.get("bias_verdict", {})
    articles_used = result.get("articles_used", [])
    ugc_posts = result.get("ugc_posts", result.get("reddit_posts", []))
    ugc_count = result.get("ugc_posts_count", result.get("reddit_posts_count", 0))

    tabs = st.tabs([
        "Overview",
        "Sentiment & Tone",
        "Framing Analysis",
        "Word Choice",
        "Agreements & Disagreements",
        "Public Opinion",
        "Sources",
    ])

    with tabs[0]:
        render_balanced_summary(balanced_summary)
        st.divider()
        render_bias_verdict(bias_verdict)
        st.divider()
        render_framing_differences(framing_diffs)

    with tabs[1]:
        cols = st.columns(len(NEWS_SOURCES))
        for col, source in zip(cols, NEWS_SOURCES):
            with col:
                if source in sentiment:
                    render_sentiment_card(source, sentiment[source])
                else:
                    st.info(f"No sentiment data for {source}.")

    with tabs[2]:
        cols = st.columns(len(NEWS_SOURCES))
        for col, source in zip(cols, NEWS_SOURCES):
            with col:
                if source in framing:
                    render_framing_card(source, framing[source])
                else:
                    st.info(f"No framing data for {source}.")

    with tabs[3]:
        render_word_choice_table(word_choice)

    with tabs[4]:
        render_agreements_disagreements(agreements, disagreements)
        st.divider()
        render_omissions_section(omissions)

    with tabs[5]:
        if ugc_posts or public_opinion_summary:
            render_public_opinion(ugc_posts, public_opinion_summary)
        else:
            st.info(
                "Public opinion data was not included in this analysis. "
                "Enable 'Include public opinion' and re-analyze."
            )

    with tabs[6]:
        render_article_sources(articles_used)
        meta_cols = st.columns(3)
        with meta_cols[0]:
            st.metric("Articles analyzed", len(articles_used))
        with meta_cols[1]:
            st.metric("UGC posts collected", ugc_count)
        with meta_cols[2]:
            live = "Yes" if result.get("live_fetch_used") else "No"
            st.metric("Live articles fetched", live)


def render_page():
    st.set_page_config(
        page_title="Multi-Perspective News Analyzer",
        layout="wide",
        page_icon="📰",
    )

    _render_sidebar()

    st.title("Multi-Perspective News Analyzer")
    st.subheader("See the same story through different eyes — BBC vs CNN vs Al Jazeera")
    st.caption("Powered by RAG + LLaMA 3.3 70B")
    st.divider()

    col_input, col_options = st.columns([3, 1])
    with col_input:
        query = st.text_input(
            "Enter a news topic",
            placeholder="e.g. Gaza ceasefire talks, Ukraine war, US elections",
            key="query_input",
        )
    with col_options:
        use_live_fetch = st.checkbox("Include live articles (NewsAPI)", value=True)
        include_ugc = st.checkbox("Include public opinion (HN + YouTube)", value=True)

    analyze_clicked = st.button("Analyze", type="primary", use_container_width=False)

    if analyze_clicked and query.strip():
        cached = get_cached_result(query.strip())
        if cached:
            ts = cached.get("timestamp", "unknown time")
            st.info(
                f"Showing cached result from {ts} UTC. "
                "Clear the cache and click Analyze again to refresh."
            )
            st.session_state["last_result"] = cached
        else:
            with render_loading_state():
                try:
                    from analysis.analyzer import analyze_topic
                    result = analyze_topic(
                        query.strip(),
                        use_live_fetch=use_live_fetch,
                        include_ugc=include_ugc,
                    )
                    if result.get("error") == "no_articles":
                        st.warning(result.get("message", "No articles found."))
                        st.session_state.pop("last_result", None)
                    else:
                        save_to_cache(query.strip(), result)
                        st.session_state["last_result"] = result
                except Exception as e:
                    tb = traceback.format_exc()
                    st.error(
                        f"**Analysis failed:** {type(e).__name__}: {e}\n\n"
                        "Try a different or broader topic, or check your API keys in `.env`."
                    )
                    with st.expander("Show error details"):
                        st.code(tb)
                    st.session_state.pop("last_result", None)

    elif analyze_clicked and not query.strip():
        st.warning("Please enter a news topic before clicking Analyze.")

    if "last_result" in st.session_state and st.session_state["last_result"]:
        result = st.session_state["last_result"]
        if not result.get("error"):
            st.divider()
            st.markdown(f"### Results for: *{result.get('query', query)}*")
            _render_results(result)
