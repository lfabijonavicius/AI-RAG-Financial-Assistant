# tools/stock_price.py
# Tool 1: Fetch the current live price for a stock or market index.
# Used when the user asks "what is AAPL's price?" or "where is the S&P 500 today?".

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

    # Try the most reliable field first, fall back to regularMarketPrice for pre/post market
    price = info.get("currentPrice") or info.get("regularMarketPrice")

    # Indices (^DJI, ^GSPC) don't populate currentPrice in .info — use fast_info instead
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
        "market_state": info.get("marketState", "unknown"),  # REGULAR, PRE, POST, CLOSED
        "exchange": info.get("exchange", ""),
        "name": info.get("shortName") or info.get("longName", symbol),
    }
