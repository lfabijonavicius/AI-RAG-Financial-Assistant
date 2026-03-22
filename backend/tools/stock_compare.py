# tools/stock_compare.py
# Tool 4 (Optional): Side-by-side comparison of multiple tickers.

import logging
import yfinance as yf
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def compare_stocks(tickers: str, period: str = "1mo") -> dict:
    """Compare multiple stocks side by side. Pass tickers as a comma-separated string
    e.g. 'AAPL,MSFT,GOOGL'. Returns key metrics and normalised price performance.
    Use this when the user wants to compare two or more stocks."""
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    results = {}

    history_series: dict = {}

    for ticker in ticker_list:
        t = yf.Ticker(ticker)
        info = t.info
        hist = t.history(period=period)
        if hist.empty:
            results[ticker] = {"error": "No data"}
            continue
        closes = hist["Close"]
        total_return = round(((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100, 2)
        results[ticker] = {
            "name": info.get("longName"),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            f"return_{period}_pct": float(total_return),
        }
        # Normalised to 100 at start so both lines are on the same scale
        base = closes.iloc[0]
        history_series[ticker] = {
            date.strftime("%m-%d"): round((price / base) * 100, 3)
            for date, price in closes.items()
        }

    return {"comparison": results, "period": period, "history": history_series}
