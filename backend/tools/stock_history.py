# tools/stock_history.py
# Tool 2: Fetch historical OHLCV price data for a ticker over a given period.
# The frontend automatically renders this as an interactive chart,
# so the agent is instructed NOT to list individual prices in its text response.

import logging
import yfinance as yf
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_stock_history(ticker: str, period: str = "1mo") -> dict:
    """Get historical stock price data for a ticker.
    period can be: 1mo, 3mo, 6mo, 1y, 2y, 5y.
    Use this when the user asks about historical performance, price trends, or wants a chart."""
    sym = ticker.upper()
    t = yf.Ticker(sym)
    hist = t.history(period=period)

    if hist.empty:
        return {"error": f"No historical data found for {ticker}"}

    # Format dates as strings for JSON serialisation
    hist.index = hist.index.strftime("%Y-%m-%d")
    rows = hist[["Open", "High", "Low", "Close", "Volume"]].round(2).to_dict("index")

    closes = hist["Close"]

    # Total return = percentage gain/loss over the full period
    total_return = round(((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100, 2)

    # Max drawdown = largest peak-to-trough decline (measures downside risk)
    rolling_max = closes.cummax()
    drawdown = ((closes - rolling_max) / rolling_max).min()
    max_drawdown = round(float(drawdown) * 100, 2)

    # Fetch the company name to display in the chart header instead of the raw ticker
    info = t.info or {}
    name = info.get("shortName") or info.get("longName") or sym

    return {
        "ticker": sym,
        "name": name,
        "period": period,
        "total_return_pct": total_return,
        "max_drawdown_pct": max_drawdown,
        "data": rows,
    }
