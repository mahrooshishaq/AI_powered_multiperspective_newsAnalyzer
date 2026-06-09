import streamlit as st

SENTIMENT_COLORS = {
    "positive": "#28a745",
    "negative": "#dc3545",
    "neutral": "#6c757d",
    "mixed": "#ffc107",
}

FRAMING_BADGES = {
    "political": "#6f42c1",
    "humanitarian": "#17a2b8",
    "security": "#dc3545",
    "economic": "#fd7e14",
    "diplomatic": "#007bff",
}


def _badge(text: str, color: str) -> str:
    return (
        f'<span style="background-color:{color};color:white;padding:2px 8px;'
        f'border-radius:12px;font-size:0.8em;font-weight:bold;">{text}</span>'
    )


def render_sentiment_card(source_name: str, sentiment_data: dict):
    label = sentiment_data.get("label", "unknown").lower()
    explanation = sentiment_data.get("explanation", "")
    loaded_words = sentiment_data.get("loaded_words", [])
    color = SENTIMENT_COLORS.get(label, "#adb5bd")

    st.markdown(
        f"""
        <div style="border:1px solid {color};border-radius:8px;padding:14px;margin-bottom:8px;">
          <h4 style="margin:0 0 6px 0;">{source_name}</h4>
          {_badge(label.upper(), color)}
          <p style="margin:8px 0 4px 0;font-size:0.9em;">{explanation}</p>
          <div>{"".join(_badge(w, "#495057") + " " for w in loaded_words)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_framing_card(source_name: str, framing_data: dict):
    angle = framing_data.get("angle", "unknown").lower()
    explanation = framing_data.get("explanation", "")
    color = FRAMING_BADGES.get(angle, "#343a40")

    st.markdown(
        f"""
        <div style="border:1px solid {color};border-radius:8px;padding:14px;margin-bottom:8px;">
          <h4 style="margin:0 0 6px 0;">{source_name}</h4>
          {_badge(angle.upper(), color)}
          <p style="margin:8px 0 0 0;font-size:0.9em;">{explanation}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_word_choice_table(word_choice_list: list):
    if not word_choice_list:
        st.info("No word choice comparisons available.")
        return

    headers = ["Concept", "BBC News", "CNN", "Al Jazeera", "Significance"]
    rows = []
    for item in word_choice_list:
        rows.append([
            item.get("concept", ""),
            item.get("bbc_word", ""),
            item.get("cnn_word", ""),
            item.get("aljazeera_word", ""),
            item.get("significance", ""),
        ])

    import pandas as pd
    df = pd.DataFrame(rows, columns=headers)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_omissions_section(omissions_dict: dict):
    if not omissions_dict:
        st.info("No omission data available.")
        return

    for source, omissions in omissions_dict.items():
        with st.expander(f"{source} — What was left out"):
            if omissions:
                for item in omissions:
                    st.markdown(f"- {item}")
            else:
                st.write("No notable omissions identified.")


def render_agreements_disagreements(agreements: list, disagreements: list):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            '<div style="background:#d4edda;border:1px solid #c3e6cb;border-radius:8px;padding:14px;">'
            '<h4 style="color:#155724;margin-top:0;">Points of Agreement</h4>',
            unsafe_allow_html=True,
        )
        for item in agreements or []:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(
            '<div style="background:#f8d7da;border:1px solid #f5c6cb;border-radius:8px;padding:14px;">'
            '<h4 style="color:#721c24;margin-top:0;">Points of Disagreement</h4>',
            unsafe_allow_html=True,
        )
        for item in disagreements or []:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)


def render_framing_differences(framing_diffs: list):
    if not framing_diffs:
        st.info("No framing differences identified.")
        return

    st.markdown("**Key Narrative Differences:**")
    for diff in framing_diffs:
        st.markdown(f"- {diff}")


def render_balanced_summary(summary: str):
    st.info(f"**Balanced Neutral Summary**\n\n{summary}")


PLATFORM_COLORS = {
    "Hacker News": "#ff6600",
    "YouTube": "#ff0000",
    "Reddit": "#ff4500",
}


def render_public_opinion(ugc_posts: list, opinion_summary: str):
    if opinion_summary:
        st.markdown(f"**Overall Public Sentiment:** {opinion_summary}")
        st.divider()

    if not ugc_posts:
        st.caption("No public opinion data available for this topic.")
        return

    for post in ugc_posts:
        title = post.get("title", "Untitled")
        score = post.get("score", 0)
        platform = post.get("platform", post.get("subreddit", "Online"))
        comments = post.get("comments", [])
        color = PLATFORM_COLORS.get(platform, "#343a40")
        score_suffix = f" (↑{score})" if score else ""
        plain_label = f"[{platform}] {title[:75]}{score_suffix}"
        with st.expander(plain_label):
            st.markdown(_badge(platform, color), unsafe_allow_html=True)
            if comments:
                st.markdown("**Top Comments:**")
                for c in comments:
                    st.markdown(f"> {c}")
            else:
                st.caption("No comments collected.")


def render_bias_verdict(verdict_dict: dict):
    if not verdict_dict:
        st.info("No bias verdict available.")
        return

    cols = st.columns(len(verdict_dict))
    for col, (source, verdict) in zip(cols, verdict_dict.items()):
        with col:
            st.markdown(
                f"""
                <div style="border:1px solid #dee2e6;border-radius:8px;padding:14px;text-align:center;">
                  <h5 style="margin:0 0 8px 0;">{source}</h5>
                  <p style="font-size:0.85em;color:#495057;margin:0;">{verdict}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_article_sources(articles_used: list):
    with st.expander("Sources Used in This Analysis"):
        if not articles_used:
            st.caption("No source metadata available.")
            return
        for article in articles_used:
            source = article.get("source", "Unknown")
            title = article.get("title", "No title")
            url = article.get("url", "")
            if url:
                st.markdown(f"- **{source}** — [{title}]({url})")
            else:
                st.markdown(f"- **{source}** — {title}")


def render_loading_state():
    return st.spinner("Fetching articles and analyzing perspectives...")
