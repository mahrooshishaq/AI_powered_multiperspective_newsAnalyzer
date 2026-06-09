from config.settings import MAX_ARTICLE_WORDS, NEWS_SOURCES
from utils.text_cleaner import truncate_to_words


def build_analysis_prompt(
    query: str,
    articles: list,
    reddit_posts: list = None,
    date_range_days: int = 0,
) -> str:
    parts = []

    parts.append(f'You are analyzing news coverage of the following topic: "{query}"\n')

    if date_range_days > 3:
        parts.append(
            f"IMPORTANT NOTE: The articles below span {date_range_days} days. "
            "Some differences you observe may be due to events that occurred between "
            "the articles' publication dates (TEMPORAL DIFFERENCES), not due to "
            "different editorial framing. "
            "When you identify a disagreement or framing difference, check whether it "
            "could be explained by the time gap. If so, label it explicitly as a "
            "temporal difference in your disagreements and framing_differences fields "
            "rather than attributing it to editorial bias.\n"
        )

    parts.append("Below are news articles retrieved from different outlets:\n")
    parts.append("=" * 60 + "\n")

    for article in articles:
        source = article.get("source", "Unknown")
        title = article.get("title", "No title")
        date = article.get("published_at", "Unknown date")
        text = truncate_to_words(article.get("text", ""), MAX_ARTICLE_WORDS)

        parts.append(f"SOURCE: {source}")
        parts.append(f"TITLE: {title}")
        parts.append(f"DATE: {date}")
        parts.append("CONTENT:")
        parts.append(text)
        parts.append("---\n")

    if reddit_posts:
        parts.append("\nPUBLIC OPINION (Hacker News, YouTube, and other platforms):")
        for i, post in enumerate(reddit_posts[:5], start=1):
            title = post.get("title", "")
            score = post.get("score", 0)
            platform = post.get("platform", post.get("subreddit", "Online"))
            comments = post.get("comments", [])
            comment_str = " | ".join(comments[:3]) if comments else "No comments"
            parts.append(f'POST {i} [{platform}]: "{title}" (upvotes/score: {score})')
            parts.append(f"Top comments: {comment_str}")
            parts.append("---")
        parts.append("")

    source_list = ", ".join([f'"{s}"' for s in NEWS_SOURCES])

    parts.append("\n" + "=" * 60)
    parts.append("TASK:")
    parts.append(
        f"Analyze the above articles and return a JSON object with exactly these keys. "
        f"Use the source names exactly as they appear: {source_list}.\n"
    )

    parts.append("""
Return a JSON object with these exact keys:

{
  "sentiment": {
    "<source_name>": {
      "label": "<positive|negative|neutral|mixed>",
      "explanation": "<one sentence>",
      "loaded_words": ["word1", "word2", "word3"]
    }
  },
  "framing": {
    "<source_name>": {
      "angle": "<political|humanitarian|security|economic|diplomatic>",
      "explanation": "<one sentence>"
    }
  },
  "word_choice": [
    {
      "concept": "<what is being described>",
      "bbc_word": "<exact word BBC used>",
      "cnn_word": "<exact word CNN used>",
      "aljazeera_word": "<exact word Al Jazeera used>",
      "significance": "<one sentence on why this difference matters>"
    }
  ],
  "omissions": {
    "<source_name>": ["<thing omitted 1>", "<thing omitted 2>"]
  },
  "agreements": ["<fact all sources agree on 1>", "<fact 2>", "<fact 3>"],
  "disagreements": ["<claim where sources contradict 1>", "<claim 2>"],
  "framing_differences": ["<most significant narrative difference 1>", "<difference 2>"],
  "balanced_summary": "<3-5 sentence neutral paragraph summarizing the event>",
  "public_opinion_summary": "<1-2 sentence summary of public opinion, or null if no UGC data>",
  "bias_verdict": {
    "<source_name>": "<one sentence overall bias verdict for this source>"
  }
}

Include 2-4 items in word_choice. Include 2-3 items in agreements, disagreements, and framing_differences.
Include 1-3 omission strings per source.

Return ONLY valid JSON. No text before or after the JSON object. Do not use markdown code blocks.
""")

    return "\n".join(parts)
