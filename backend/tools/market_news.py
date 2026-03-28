# tools/market_news.py
# Fetch recent market/topic news via Alpha Vantage News & Sentiment API.
# Use this for commodities, macro topics, indices — anything yfinance news can't cover.

import logging
import httpx
from langchain_core.tools import tool
from config import settings

logger = logging.getLogger(__name__)

TOPIC_MAP = {
    "oil": "energy_transportation",
    "energy": "energy_transportation",
    "crude": "energy_transportation",
    "gas": "energy_transportation",
    "inflation": "economy_macro",
    "macro": "economy_macro",
    "economy": "economy_macro",
    "gdp": "economy_macro",
    "interest rate": "economy_monetary",
    "fed": "economy_monetary",
    "federal reserve": "economy_monetary",
    "rates": "economy_monetary",
    "crypto": "blockchain",
    "bitcoin": "blockchain",
    "ethereum": "blockchain",
    "ipo": "ipo",
    "merger": "mergers_and_acquisitions",
    "acquisition": "mergers_and_acquisitions",
    "earnings": "earnings",
    "real estate": "real_estate",
    "housing": "real_estate",
    "tech": "technology",
    "technology": "technology",
    "market": "financial_markets",
    "stocks": "financial_markets",
    "finance": "finance",
}


@tool
def get_market_news(topic: str) -> list[dict] | dict:
    """Get recent news and sentiment for a market topic or commodity.
    Use this for broad market topics such as: oil, energy, inflation, interest rates,
    the Fed, crypto, Bitcoin, IPOs, mergers, real estate, technology, or general market news.
    Also use this when the user asks why a commodity or index moved.
    Pass a plain English topic (e.g. 'oil', 'inflation', 'crypto', 'market')."""
    if not settings.alpha_vantage_api_key:
        return {"error": "ALPHA_VANTAGE_API_KEY not configured"}

    # Map plain-English topic to Alpha Vantage topic category
    key = topic.lower().strip()
    av_topic = next((v for k, v in TOPIC_MAP.items() if k in key), "financial_markets")

    try:
        response = httpx.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "NEWS_SENTIMENT",
                "topics": av_topic,
                "limit": 6,
                "sort": "LATEST",
                "apikey": settings.alpha_vantage_api_key,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        articles = data.get("feed", [])
        if not articles:
            return {"error": f"No news found for topic: {topic}"}

        return [
            {
                "title": a.get("title", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
                "published_at": a.get("time_published", ""),
                "summary": a.get("summary", ""),
                "sentiment": a.get("overall_sentiment_label", ""),
            }
            for a in articles[:5]
        ]
    except Exception as e:
        logger.error(f"Alpha Vantage news error for topic '{topic}': {e}")
        return {"error": str(e)}
