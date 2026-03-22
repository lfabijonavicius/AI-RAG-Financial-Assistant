# tools/portfolio.py
# Tool 6 (Optional): Calculate basic portfolio risk metrics.

import logging
import numpy as np
import yfinance as yf
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.05  # annualised, approximate


@tool
def calculate_portfolio_risk(tickers: str, weights: str) -> dict:
    """Calculate portfolio risk metrics for a set of stocks.
    Pass tickers as comma-separated string (e.g. 'AAPL,MSFT') and
    weights as comma-separated decimals that sum to 1 (e.g. '0.6,0.4').
    Returns expected return, volatility, Sharpe ratio, and correlation matrix."""
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    weight_list = [float(w.strip()) for w in weights.split(",")]

    if len(ticker_list) != len(weight_list):
        return {"error": "Number of tickers and weights must match"}
    if round(sum(weight_list), 4) != 1.0:
        return {"error": f"Weights must sum to 1.0, got {sum(weight_list):.4f}"}

    data = yf.download(ticker_list, period="1y", auto_adjust=True, progress=False)["Close"]
    if data.empty:
        return {"error": "Could not retrieve price data"}

    returns = data.pct_change().dropna()
    w = np.array(weight_list)

    portfolio_return = float(np.dot(w, returns.mean()) * 252)
    cov_matrix = returns.cov() * 252
    portfolio_volatility = float(np.sqrt(w @ cov_matrix.values @ w))
    sharpe = round((portfolio_return - RISK_FREE_RATE) / portfolio_volatility, 2)

    return {
        "tickers": ticker_list,
        "weights": weight_list,
        "expected_annual_return_pct": round(portfolio_return * 100, 2),
        "annual_volatility_pct": round(portfolio_volatility * 100, 2),
        "sharpe_ratio": sharpe,
        "correlation_matrix": returns.corr().round(3).to_dict(),
    }
