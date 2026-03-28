# tools/registry.py
# Single import point for all LangChain tools.
# The agent imports TOOLS from here only — never imports individual tool files directly.

from tools.stock_price import get_stock_price
from tools.stock_history import get_stock_history
from tools.fundamentals import get_fundamentals
from tools.stock_compare import compare_stocks
from tools.news import get_company_news
from tools.market_news import get_market_news
from tools.portfolio import calculate_portfolio_risk

TOOLS = [
    get_stock_price,
    get_stock_history,
    get_fundamentals,
    compare_stocks,
    get_company_news,
    get_market_news,
    calculate_portfolio_risk,
]
