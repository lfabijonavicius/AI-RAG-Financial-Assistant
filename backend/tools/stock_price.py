# tools/stock_price.py
# Tool 1 (Core): Get the current live stock price for a ticker symbol.

import logging
import yfinance as yf
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_stock_price(ticker: str) -> dict:
    """Get the current stock price or index level for a ticker symbol (e.g. AAPL, TSLA, MSFT)
    or a market index (e.g. ^DJI for Dow Jones, ^GSPC for S&P 500, ^IXIC for NASDAQ).
    Use this when the user asks for the current or latest price of a stock or index."""
    symbol = ticker.upper()
    t = yf.Ticker(symbol)
    info = t.info
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    # Fallback for indices which don't populate currentPrice in .info
    if price is None:
        try:
            price = t.fast_info.last_price
        except Exception:
            pass
    if price is None:
        return {"error": f"Could not retrieve price for {ticker}"}
    return {
        "ticker": symbol,
        "price": price,
        "currency": info.get("currency", "USD"),
        "market_state": info.get("marketState", "unknown"),
        "exchange": info.get("exchange", ""),
        "name": info.get("shortName") or info.get("longName", symbol),
    }
