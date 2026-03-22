# tools/stock_history.py
# Tool 2 (Core): Get historical OHLCV data for a ticker over a given period.

import logging
import yfinance as yf
import pandas as pd
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_stock_history(ticker: str, period: str = "1mo") -> dict:
    """Get historical stock price data for a ticker.
    period can be: 1mo, 3mo, 6mo, 1y, 2y, 5y.
    Use this when the user asks about historical performance, price trends, or wants a chart."""
    t = yf.Ticker(ticker.upper())
    hist = t.history(period=period)
    if hist.empty:
        return {"error": f"No historical data found for {ticker}"}

    hist.index = hist.index.strftime("%Y-%m-%d")
    rows = hist[["Open", "High", "Low", "Close", "Volume"]].round(2).to_dict("index")

    closes = hist["Close"]
    total_return = round(((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100, 2)
    rolling_max = closes.cummax()
    drawdown = ((closes - rolling_max) / rolling_max).min()
    max_drawdown = round(float(drawdown) * 100, 2)

    return {
        "ticker": ticker.upper(),
        "period": period,
        "total_return_pct": total_return,
        "max_drawdown_pct": max_drawdown,
        "data": rows,
    }
