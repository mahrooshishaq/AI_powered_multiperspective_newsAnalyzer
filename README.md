# Multi-Perspective News Analyzer

A RAG-powered system that retrieves news articles from BBC News, CNN, and Al Jazeera on any topic and uses LLaMA 3.3 70B to compare how each outlet frames the story — analyzing sentiment, framing angle, word choice, omissions, and more.

## Prerequisites

- Python 3.10+
- pip

## Setup

```bash
# 1. Clone the repo and enter the project folder
cd news_analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Fill in your API keys
cp .env .env.local   # or just edit .env directly
# Edit .env and replace placeholder values with real keys

# 4. Populate the vector database (run once)
python data/ingest.py

# 5. Start the app
streamlit run app.py
```

## API Keys

| Key | Where to get it |
|---|---|
| `NEWSAPI_KEY` | https://newsapi.org |
| `GROQ_API_KEY` | https://console.groq.com |
| `GEMINI_API_KEY` | https://aistudio.google.com |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | https://www.reddit.com/prefs/apps |

## How to Run

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Known Limitations

- NewsAPI free tier returns truncated article content (~200 characters). The system combines title, description, and content fields to maximize text.
- CC-News articles in the vector database may be from 2016–2019. Enable live fetching (NewsAPI) for current events.
- Groq free tier has rate limits (~30 requests/minute). High usage may trigger temporary blocks — the system automatically falls back to Gemini.
- BAAI/bge-m3 (~2.3 GB) is downloaded on first run from HuggingFace. Subsequent runs use the local cache.
- Reddit API rate limit: 60 requests/minute (handled automatically by PRAW).
- The cross-encoder reranker adds ~2–3 seconds to response time but significantly improves retrieval quality.
