# tools/market_news.py
# Fetch recent market/topic news via Alpha Vantage News & Sentiment API.
# Uses ticker-based filtering for sectors (more relevant) and topic categories for macro.

import logging
import httpx
from langchain_core.tools import tool
from config import settings

logger = logging.getLogger(__name__)

# Sector/theme → representative ETF tickers (gives much more relevant results than broad topics)
TICKER_MAP: dict[str, str] = {
    "solar": "TAN,FSLR,ENPH,SEDG",
    "clean energy": "ICLN,TAN,QCLN",
    "renewable": "ICLN,TAN,NEE",
    "wind": "FAN,NEE,ICLN",
    "nuclear": "URA,CCJ,NNE",
    "ev": "TSLA,RIVN,LCID,NIO",
    "electric vehicle": "TSLA,RIVN,LCID,NIO",
    "semiconductor": "NVDA,AMD,INTC,SOXX",
    "chip": "NVDA,AMD,INTC,TSM",
    "ai": "NVDA,MSFT,GOOGL,META",
    "artificial intelligence": "NVDA,MSFT,GOOGL,META",
    "gold": "GLD,GDX,NEM,GOLD",
    "silver": "SLV,AG,PAAS",
    "copper": "COPA,FCX,SCCO",
    "bitcoin": "BTC,MSTR,COIN",
    "crypto": "BTC,ETH,COIN,MSTR",
    "ethereum": "ETH,COIN",
    "bank": "JPM,BAC,WFC,GS,XLF",
    "banking": "JPM,BAC,WFC,GS,XLF",
    "pharma": "JNJ,PFE,MRK,XPH",
    "biotech": "MRNA,GILD,BIIB,XBI",
    "healthcare": "UNH,JNJ,ABT,XLV",
    "real estate": "VNQ,AMT,PLD,SPG",
    "reit": "VNQ,AMT,PLD,SPG",
    "defence": "LMT,RTX,NOC,ITA",
    "defense": "LMT,RTX,NOC,ITA",
}

# Macro topics → Alpha Vantage topic category
TOPIC_MAP: dict[str, str] = {
    "oil": "energy_transportation",
    "crude": "energy_transportation",
    "gas": "energy_transportation",
    "energy": "energy_transportation",
    "inflation": "economy_macro",
    "gdp": "economy_macro",
    "recession": "economy_macro",
    "economy": "economy_macro",
    "interest rate": "economy_monetary",
    "fed": "economy_monetary",
    "federal reserve": "economy_monetary",
    "rates": "economy_monetary",
    "ipo": "ipo",
    "merger": "mergers_and_acquisitions",
    "acquisition": "mergers_and_acquisitions",
    "earnings": "earnings",
    "market": "financial_markets",
    "stocks": "financial_markets",
    "finance": "finance",
    "technology": "technology",
    "tech": "technology",
    "manufacturing": "manufacturing",
    "retail": "retail_wholesale",
}


@tool
def get_market_news(topic: str) -> list[dict] | dict:
    """Get recent news and sentiment for a market topic, sector, or commodity.
    Use this for: specific sectors (solar, EV, semiconductors, biotech, defence),
    commodities (oil, gold, copper), macro topics (inflation, interest rates, Fed, GDP),
    crypto (Bitcoin, Ethereum), or general market news.
    Also use this when the user asks why something moved or wants investment news on a theme.
    Pass a plain English topic (e.g. 'solar', 'oil', 'inflation', 'AI', 'crypto')."""
    if not settings.alpha_vantage_api_key:
        return {"error": "ALPHA_VANTAGE_API_KEY not configured"}

    key = topic.lower().strip()

    # Prefer ticker-based lookup for sectors (more specific results)
    tickers = next((v for k, v in TICKER_MAP.items() if k in key), None)
    av_topic = None if tickers else next((v for k, v in TOPIC_MAP.items() if k in key), "financial_markets")

    params: dict = {
        "function": "NEWS_SENTIMENT",
        "sort": "LATEST",
        "apikey": settings.alpha_vantage_api_key,
    }
    if tickers:
        params["tickers"] = tickers
    else:
        params["topics"] = av_topic

    try:
        response = httpx.get(
            "https://www.alphavantage.co/query",
            params=params,
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
