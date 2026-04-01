# tools/registry.py
# Single import point for all LangChain tools.
# The agent imports TOOLS from here — it never imports individual tool files directly.
# To add a new tool: create the file, define the @tool function, and add it here.

from tools.stock_price import get_stock_price
from tools.stock_history import get_stock_history
from tools.fundamentals import get_fundamentals
from tools.stock_compare import compare_stocks
from tools.news import get_company_news
from tools.market_news import get_market_news
from tools.portfolio import calculate_portfolio_risk

TOOLS = [
    get_stock_price,          # Live price for a ticker or index
    get_stock_history,        # Historical OHLCV data + chart
    get_fundamentals,         # P/E, market cap, EPS, dividend yield etc.
    compare_stocks,           # Side-by-side comparison with normalised chart
    get_company_news,         # Recent headlines for a specific stock (via yfinance)
    get_market_news,          # Sector/macro news via Alpha Vantage (oil, inflation etc.)
    calculate_portfolio_risk, # Sharpe ratio, volatility, correlation matrix
]
