# tests/conftest.py
# Shared fixtures and environment setup.
# This file is loaded by pytest before any test module, so env vars are set
# before pydantic-settings reads them — no real .env values are needed in CI.

import os
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

# --- Dummy env vars so config.py doesn't raise ValidationError in CI ---
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("NEWS_API_KEY", "test-news-key")


def _make_history(start: float = 170.0, end: float = 182.0, periods: int = 22) -> pd.DataFrame:
    """Return a realistic OHLCV DataFrame for mocking yfinance history."""
    dates = pd.date_range("2024-01-01", periods=periods, freq="B")
    closes = np.linspace(start, end, periods)
    return pd.DataFrame(
        {
            "Open": closes - 1.0,
            "High": closes + 2.0,
            "Low": closes - 2.0,
            "Close": closes,
            "Volume": [50_000_000] * periods,
        },
        index=dates,
    )


@pytest.fixture
def aapl_info() -> dict:
    return {
        "currentPrice": 182.50,
        "currency": "USD",
        "marketState": "REGULAR",
        "exchange": "NASDAQ",
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "marketCap": 2_800_000_000_000,
        "trailingPE": 28.5,
        "forwardPE": 25.1,
        "trailingEps": 6.41,
        "dividendYield": 0.0055,
        "fiftyTwoWeekHigh": 199.62,
        "fiftyTwoWeekLow": 143.90,
        "fiftyDayAverage": 175.30,
        "twoHundredDayAverage": 168.45,
        "sector": "Technology",
        "industry": "Consumer Electronics",
    }


@pytest.fixture
def mock_ticker(aapl_info):
    """Mock yfinance.Ticker instance pre-loaded with AAPL data."""
    t = MagicMock()
    t.info = aapl_info
    t.history.return_value = _make_history()
    t.fast_info.last_price = 182.50
    return t


@pytest.fixture
def mock_download_df():
    """Mock return value for yf.download([AAPL, MSFT], ...)['Close']."""
    dates = pd.date_range("2024-01-01", periods=22, freq="B")
    return pd.DataFrame(
        {
            "AAPL": np.linspace(170, 182, 22),
            "MSFT": np.linspace(360, 380, 22),
        },
        index=dates,
    )
