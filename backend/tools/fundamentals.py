# tools/fundamentals.py
# Tool 3: Fetch key fundamental financial metrics for a stock.
# Fundamentals help investors assess whether a stock is overvalued or undervalued
# and understand the company's financial health beyond just the price.

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
        "market_cap": info.get("marketCap"),           # Total company value
        "pe_ratio": info.get("trailingPE"),            # Price-to-earnings (trailing 12 months)
        "forward_pe": info.get("forwardPE"),           # P/E based on next year's estimated earnings
        "eps": info.get("trailingEps"),                # Earnings per share
        "dividend_yield": info.get("dividendYield"),   # Annual dividend as % of price
        "52w_high": info.get("fiftyTwoWeekHigh"),      # Highest price in the past year
        "52w_low": info.get("fiftyTwoWeekLow"),        # Lowest price in the past year
        "50d_avg": info.get("fiftyDayAverage"),        # Short-term trend indicator
        "200d_avg": info.get("twoHundredDayAverage"),  # Long-term trend indicator
    }
