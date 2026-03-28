# tools/news.py
# Tool 5: Fetch recent news headlines for a company via yfinance (no API key required).

import logging
import yfinance as yf
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_company_news(ticker: str) -> list[dict] | dict:
    """Get recent news headlines for a company or market index.
    Pass the ticker symbol (e.g. 'AAPL', 'TSLA', '^GSPC' for S&P 500).
    Use this when the user asks about recent news, events, or sentiment around a company or the market."""
    try:
        t = yf.Ticker(ticker.upper())
        articles = t.news or []
        if not articles:
            return {"error": f"No news found for {ticker.upper()}"}
        return [
            {
                "title": a.get("content", {}).get("title", ""),
                "source": a.get("content", {}).get("provider", {}).get("displayName", ""),
                "url": a.get("content", {}).get("canonicalUrl", {}).get("url", ""),
                "published_at": a.get("content", {}).get("pubDate", ""),
                "summary": a.get("content", {}).get("summary", ""),
            }
            for a in articles[:5]
        ]
    except Exception as e:
        logger.error(f"News fetch error for {ticker}: {e}")
        return {"error": str(e)}
