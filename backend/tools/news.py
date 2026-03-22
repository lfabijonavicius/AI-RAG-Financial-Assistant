# tools/news.py
# Tool 5 (Optional): Fetch recent news headlines for a company via NewsAPI.

import logging
import httpx
from langchain_core.tools import tool
from config import settings

logger = logging.getLogger(__name__)


@tool
def get_company_news(company_name: str) -> list[dict] | dict:
    """Get recent news headlines for a company. Pass the company name (e.g. 'Apple', 'Tesla').
    Use this when the user asks about recent news, events, or sentiment around a company."""
    if not settings.news_api_key:
        return {"error": "NEWS_API_KEY not configured"}

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": company_name,
        "sortBy": "publishedAt",
        "pageSize": 5,
        "language": "en",
        "apiKey": settings.news_api_key,
    }
    response = httpx.get(url, params=params, timeout=10)
    response.raise_for_status()
    articles = response.json().get("articles", [])

    return [
        {
            "title": a["title"],
            "source": a["source"]["name"],
            "url": a["url"],
            "published_at": a["publishedAt"],
        }
        for a in articles
    ]
