# tests/test_tools.py
# Unit tests for all LangChain financial tools.
# yfinance and httpx are fully mocked — no real network calls are made.

from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# get_stock_price
# ---------------------------------------------------------------------------

class TestGetStockPrice:
    def test_returns_price_and_metadata(self, mock_ticker):
        with patch("tools.stock_price.yf.Ticker", return_value=mock_ticker):
            from tools.stock_price import get_stock_price
            result = get_stock_price.invoke({"ticker": "aapl"})

        assert result["ticker"] == "AAPL"
        assert result["price"] == pytest.approx(182.50)
        assert result["currency"] == "USD"
        assert "market_state" in result
        assert "name" in result

    def test_ticker_is_uppercased(self, mock_ticker):
        with patch("tools.stock_price.yf.Ticker", return_value=mock_ticker):
            from tools.stock_price import get_stock_price
            result = get_stock_price.invoke({"ticker": "aapl"})

        assert result["ticker"] == "AAPL"

    def test_falls_back_to_fast_info_when_info_missing(self, mock_ticker):
        mock_ticker.info = {}  # no currentPrice / regularMarketPrice
        mock_ticker.fast_info.last_price = 175.00
        with patch("tools.stock_price.yf.Ticker", return_value=mock_ticker):
            from tools.stock_price import get_stock_price
            result = get_stock_price.invoke({"ticker": "AAPL"})

        assert result["price"] == pytest.approx(175.00)

    def test_returns_error_when_no_price_available(self):
        bad_ticker = MagicMock()
        bad_ticker.info = {}
        bad_ticker.fast_info.last_price = None
        with patch("tools.stock_price.yf.Ticker", return_value=bad_ticker):
            from tools.stock_price import get_stock_price
            result = get_stock_price.invoke({"ticker": "INVALID"})

        assert "error" in result


# ---------------------------------------------------------------------------
# get_stock_history
# ---------------------------------------------------------------------------

class TestGetStockHistory:
    def test_returns_expected_keys(self, mock_ticker):
        with patch("tools.stock_history.yf.Ticker", return_value=mock_ticker):
            from tools.stock_history import get_stock_history
            result = get_stock_history.invoke({"ticker": "AAPL", "period": "1mo"})

        assert result["ticker"] == "AAPL"
        assert result["period"] == "1mo"
        assert "data" in result
        assert "total_return_pct" in result
        assert "max_drawdown_pct" in result

    def test_data_has_ohlcv_keys(self, mock_ticker):
        with patch("tools.stock_history.yf.Ticker", return_value=mock_ticker):
            from tools.stock_history import get_stock_history
            result = get_stock_history.invoke({"ticker": "AAPL", "period": "1mo"})

        first_row = next(iter(result["data"].values()))
        for key in ("Open", "High", "Low", "Close", "Volume"):
            assert key in first_row

    def test_positive_return_for_rising_price(self, mock_ticker):
        # history goes from 170 → 182, should be a positive return
        with patch("tools.stock_history.yf.Ticker", return_value=mock_ticker):
            from tools.stock_history import get_stock_history
            result = get_stock_history.invoke({"ticker": "AAPL", "period": "1mo"})

        assert result["total_return_pct"] > 0

    def test_returns_error_on_empty_history(self):
        empty_ticker = MagicMock()
        empty_ticker.history.return_value = pd.DataFrame()
        with patch("tools.stock_history.yf.Ticker", return_value=empty_ticker):
            from tools.stock_history import get_stock_history
            result = get_stock_history.invoke({"ticker": "FAKE", "period": "1mo"})

        assert "error" in result


# ---------------------------------------------------------------------------
# get_fundamentals
# ---------------------------------------------------------------------------

class TestGetFundamentals:
    def test_returns_key_metrics(self, mock_ticker):
        with patch("tools.fundamentals.yf.Ticker", return_value=mock_ticker):
            from tools.fundamentals import get_fundamentals
            result = get_fundamentals.invoke({"ticker": "AAPL"})

        assert result["ticker"] == "AAPL"
        assert result["pe_ratio"] == pytest.approx(28.5)
        assert result["market_cap"] == 2_800_000_000_000
        assert result["52w_high"] == pytest.approx(199.62)
        assert result["52w_low"] == pytest.approx(143.90)

    def test_returns_sector_and_industry(self, mock_ticker):
        with patch("tools.fundamentals.yf.Ticker", return_value=mock_ticker):
            from tools.fundamentals import get_fundamentals
            result = get_fundamentals.invoke({"ticker": "AAPL"})

        assert result["sector"] == "Technology"
        assert result["industry"] == "Consumer Electronics"

    def test_handles_missing_optional_fields(self, mock_ticker):
        # Remove optional fields — should still return without error
        mock_ticker.info.pop("dividendYield", None)
        mock_ticker.info.pop("forwardPE", None)
        with patch("tools.fundamentals.yf.Ticker", return_value=mock_ticker):
            from tools.fundamentals import get_fundamentals
            result = get_fundamentals.invoke({"ticker": "AAPL"})

        assert result["dividend_yield"] is None
        assert result["forward_pe"] is None

    def test_returns_error_when_info_empty(self):
        bad_ticker = MagicMock()
        bad_ticker.info = {}
        with patch("tools.fundamentals.yf.Ticker", return_value=bad_ticker):
            from tools.fundamentals import get_fundamentals
            result = get_fundamentals.invoke({"ticker": "FAKE"})

        assert "error" in result


# ---------------------------------------------------------------------------
# compare_stocks
# ---------------------------------------------------------------------------

class TestCompareStocks:
    def _make_ticker(self, name: str, price: float, start: float, end: float) -> MagicMock:
        dates = pd.date_range("2024-01-01", periods=22, freq="B")
        closes = np.linspace(start, end, 22)
        t = MagicMock()
        t.info = {"longName": name, "currentPrice": price, "marketCap": 1_000_000_000,
                  "trailingPE": 20.0, "fiftyTwoWeekHigh": end + 10, "fiftyTwoWeekLow": start - 10}
        t.history.return_value = pd.DataFrame(
            {"Open": closes, "High": closes + 1, "Low": closes - 1,
             "Close": closes, "Volume": [1_000_000] * 22},
            index=dates,
        )
        return t

    def test_returns_both_tickers(self):
        aapl = self._make_ticker("Apple Inc.", 182.50, 170, 182)
        msft = self._make_ticker("Microsoft", 380.00, 360, 380)

        def side_effect(ticker):
            return aapl if ticker == "AAPL" else msft

        with patch("tools.stock_compare.yf.Ticker", side_effect=side_effect):
            from tools.stock_compare import compare_stocks
            result = compare_stocks.invoke({"tickers": "AAPL,MSFT", "period": "1mo"})

        assert "AAPL" in result["comparison"]
        assert "MSFT" in result["comparison"]

    def test_return_pct_key_includes_period(self):
        aapl = self._make_ticker("Apple Inc.", 182.50, 170, 182)
        with patch("tools.stock_compare.yf.Ticker", return_value=aapl):
            from tools.stock_compare import compare_stocks
            result = compare_stocks.invoke({"tickers": "AAPL", "period": "3mo"})

        assert "return_3mo_pct" in result["comparison"]["AAPL"]

    def test_history_normalised_to_100(self):
        aapl = self._make_ticker("Apple Inc.", 182.50, 170, 182)
        with patch("tools.stock_compare.yf.Ticker", return_value=aapl):
            from tools.stock_compare import compare_stocks
            result = compare_stocks.invoke({"tickers": "AAPL", "period": "1mo"})

        # First value in history should be 100 (normalised base)
        first_value = next(iter(result["history"]["AAPL"].values()))
        assert first_value == pytest.approx(100.0, abs=0.01)

    def test_empty_history_returns_error_for_ticker(self):
        bad = MagicMock()
        bad.history.return_value = pd.DataFrame()
        with patch("tools.stock_compare.yf.Ticker", return_value=bad):
            from tools.stock_compare import compare_stocks
            result = compare_stocks.invoke({"tickers": "FAKE", "period": "1mo"})

        assert result["comparison"]["FAKE"].get("error") == "No data"


# ---------------------------------------------------------------------------
# get_company_news
# ---------------------------------------------------------------------------

class TestGetCompanyNews:
    def _yf_articles(self):
        return [
            {"content": {"title": "Apple hits record", "provider": {"displayName": "Reuters"},
             "canonicalUrl": {"url": "https://reuters.com/1"}, "pubDate": "2024-01-01T10:00:00Z", "summary": "Summary 1"}},
            {"content": {"title": "AAPL earnings beat", "provider": {"displayName": "Bloomberg"},
             "canonicalUrl": {"url": "https://bloomberg.com/2"}, "pubDate": "2024-01-02T10:00:00Z", "summary": "Summary 2"}},
        ]

    def test_returns_list_of_articles(self):
        import tools.news as news_mod
        mock_ticker = MagicMock()
        mock_ticker.news = self._yf_articles()
        with patch.object(news_mod.yf, "Ticker", return_value=mock_ticker):
            result = news_mod.get_company_news.invoke({"ticker": "AAPL"})

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["title"] == "Apple hits record"
        assert result[0]["source"] == "Reuters"
        assert "url" in result[0]
        assert "published_at" in result[0]

    def test_returns_error_when_no_articles(self):
        import tools.news as news_mod
        mock_ticker = MagicMock()
        mock_ticker.news = []
        with patch.object(news_mod.yf, "Ticker", return_value=mock_ticker):
            result = news_mod.get_company_news.invoke({"ticker": "FAKE"})

        assert "error" in result

    def test_returns_error_on_exception(self):
        import tools.news as news_mod
        with patch.object(news_mod.yf, "Ticker", side_effect=Exception("network error")):
            result = news_mod.get_company_news.invoke({"ticker": "AAPL"})

        assert "error" in result


# ---------------------------------------------------------------------------
# calculate_portfolio_risk
# ---------------------------------------------------------------------------

class TestCalculatePortfolioRisk:
    def test_returns_risk_metrics(self, mock_download_df):
        with patch("tools.portfolio.yf.download") as mock_dl:
            mock_dl.return_value.__getitem__.return_value = mock_download_df
            from tools.portfolio import calculate_portfolio_risk
            result = calculate_portfolio_risk.invoke({"tickers": "AAPL,MSFT", "weights": "0.6,0.4"})

        assert "expected_annual_return_pct" in result
        assert "annual_volatility_pct" in result
        assert "sharpe_ratio" in result
        assert "correlation_matrix" in result

    def test_mismatched_tickers_and_weights_returns_error(self):
        from tools.portfolio import calculate_portfolio_risk
        result = calculate_portfolio_risk.invoke({"tickers": "AAPL,MSFT", "weights": "1.0"})
        assert "error" in result

    def test_weights_not_summing_to_one_returns_error(self):
        from tools.portfolio import calculate_portfolio_risk
        result = calculate_portfolio_risk.invoke({"tickers": "AAPL,MSFT", "weights": "0.5,0.3"})
        assert "error" in result

    def test_weights_sum_to_one(self, mock_download_df):
        with patch("tools.portfolio.yf.download") as mock_dl:
            mock_dl.return_value = MagicMock(**{"__getitem__": lambda self, key: mock_download_df})
            from tools.portfolio import calculate_portfolio_risk
            result = calculate_portfolio_risk.invoke({"tickers": "AAPL,MSFT", "weights": "0.6,0.4"})

        assert result["weights"] == [0.6, 0.4]
        assert abs(sum(result["weights"]) - 1.0) < 1e-6
