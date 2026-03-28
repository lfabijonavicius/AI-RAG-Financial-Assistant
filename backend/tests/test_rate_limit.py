# tests/test_rate_limit.py
# Unit tests for per-user daily rate limiting logic.
# Supabase is fully mocked — no real DB calls are made.

from unittest.mock import patch, MagicMock
from fastapi import HTTPException
import pytest


def _supabase_with_count(count: int) -> MagicMock:
    """Return a mock supabase client whose api_usage query returns `count`."""
    mock_result = MagicMock()
    mock_result.data = [{"request_count": count}]
    mock_sb = MagicMock()
    (mock_sb.table.return_value
              .select.return_value
              .eq.return_value
              .eq.return_value
              .execute.return_value) = mock_result
    return mock_sb


def _supabase_no_row() -> MagicMock:
    """Return a mock supabase client with no usage row for today."""
    mock_result = MagicMock()
    mock_result.data = []
    mock_sb = MagicMock()
    (mock_sb.table.return_value
              .select.return_value
              .eq.return_value
              .eq.return_value
              .execute.return_value) = mock_result
    return mock_sb


class TestCheckRateLimit:
    def test_no_usage_row_passes(self):
        """First request of the day (no DB row yet) must not be blocked."""
        with patch("db.rate_limit.supabase", _supabase_no_row()):
            from db.rate_limit import check_rate_limit
            check_rate_limit("new_user")  # should not raise

    def test_under_limit_passes(self):
        with patch("db.rate_limit.supabase", _supabase_with_count(10)):
            from db.rate_limit import check_rate_limit
            check_rate_limit("user_123")  # should not raise

    def test_at_limit_raises_429(self):
        with patch("db.rate_limit.supabase", _supabase_with_count(50)):
            from db.rate_limit import check_rate_limit
            with pytest.raises(HTTPException) as exc_info:
                check_rate_limit("user_123")
            assert exc_info.value.status_code == 429

    def test_error_message_contains_limit(self):
        with patch("db.rate_limit.supabase", _supabase_with_count(50)):
            from db.rate_limit import check_rate_limit
            with pytest.raises(HTTPException) as exc_info:
                check_rate_limit("user_123")
            assert "50" in exc_info.value.detail

    def test_one_below_limit_passes(self):
        with patch("db.rate_limit.supabase", _supabase_with_count(49)):
            from db.rate_limit import check_rate_limit
            check_rate_limit("user_123")  # 49 < 50, should not raise


class TestIncrementUsage:
    def test_calls_rpc(self):
        mock_sb = MagicMock()
        with patch("db.rate_limit.supabase", mock_sb):
            from db.rate_limit import increment_usage
            increment_usage("user_123")
        mock_sb.rpc.assert_called_once_with(
            "increment_api_usage", {"uid": "user_123"}
        )
