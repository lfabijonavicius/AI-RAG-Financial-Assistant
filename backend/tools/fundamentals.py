# tools/fundamentals.py
# Tool 3 (Core): Get key fundamental metrics for a ticker.

import logging
import yfinance as yf
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_fundamentals(ticker: str) -> dict:
    """Get fundamental financial metrics for a stock ticker: P/E ratio, market cap,
    52-week high/low, moving averages, EPS, dividend yield, sector and industry.
    Use this when the user asks about valuation, company size, or financial health."""
    t = yf.Ticker(ticker.upper())
    info = t.info
    if not info:
        return {"error": f"No fundamental data found for {ticker}"}

    return {
        "ticker": ticker.upper(),
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "eps": info.get("trailingEps"),
        "dividend_yield": info.get("dividendYield"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "50d_avg": info.get("fiftyDayAverage"),
        "200d_avg": info.get("twoHundredDayAverage"),
    }
