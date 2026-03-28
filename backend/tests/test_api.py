# tests/test_api.py
# Integration tests for FastAPI endpoints using TestClient.
# External services (Supabase, yfinance, agent) are mocked.

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest
import io


def _make_client():
    """Import app fresh with all external clients mocked."""
    with patch("db.supabase.create_client", return_value=MagicMock()):
        from main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def client():
    with patch("db.supabase.create_client", return_value=MagicMock()):
        from main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self, client):
        with patch("main.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock()
            resp = client.get("/health")
        assert resp.status_code == 200

    def test_response_has_status_ok(self, client):
        with patch("main.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock()
            resp = client.get("/health")
        assert resp.json()["status"] == "ok"

    def test_vectordb_false_when_supabase_raises(self, client):
        with patch("main.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("DB down")
            resp = client.get("/health")
        assert resp.json()["vectordb_ready"] is False


# ---------------------------------------------------------------------------
# POST /documents/upload  (input validation — no Supabase needed for these)
# ---------------------------------------------------------------------------

class TestDocumentUpload:
    def test_rejects_non_pdf_extension(self, client):
        resp = client.post(
            "/documents/upload",
            files={"file": ("report.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    def test_rejects_file_without_extension(self, client):
        resp = client.post(
            "/documents/upload",
            files={"file": ("report", b"hello", "application/octet-stream")},
        )
        assert resp.status_code == 400

    def test_rejects_oversized_pdf(self, client):
        big_content = b"%PDF-1.4 " + b"x" * (10 * 1024 * 1024 + 1)
        with patch("main.supabase") as mock_sb:
            mock_sb.storage.from_.return_value.list.return_value = []
            resp = client.post(
                "/documents/upload",
                files={"file": ("big.pdf", big_content, "application/pdf")},
            )
        assert resp.status_code == 400
        assert "large" in resp.json()["detail"].lower()

    def test_rejects_when_file_limit_reached(self, client):
        existing = [{"name": f"file{i}.pdf"} for i in range(10)]
        with patch("main.supabase") as mock_sb:
            mock_sb.storage.from_.return_value.list.return_value = existing
            resp = client.post(
                "/documents/upload",
                files={"file": ("new.pdf", b"%PDF-1.4 content", "application/pdf")},
            )
        assert resp.status_code == 400
        assert "limit" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------

class TestListDocuments:
    def test_returns_files_list(self, client):
        files = [{"name": "nvidia10k.pdf", "metadata": {"size": 1024}}]
        with patch("main.supabase") as mock_sb:
            mock_sb.storage.from_.return_value.list.return_value = files
            resp = client.get("/documents")
        assert resp.status_code == 200
        assert len(resp.json()["files"]) == 1
        assert resp.json()["files"][0]["name"] == "nvidia10k.pdf"

    def test_excludes_empty_folder_placeholder(self, client):
        files = [
            {"name": ".emptyFolderPlaceholder", "metadata": {}},
            {"name": "real.pdf", "metadata": {"size": 512}},
        ]
        with patch("main.supabase") as mock_sb:
            mock_sb.storage.from_.return_value.list.return_value = files
            resp = client.get("/documents")
        names = [f["name"] for f in resp.json()["files"]]
        assert ".emptyFolderPlaceholder" not in names
        assert "real.pdf" in names

    def test_returns_empty_list_on_error(self, client):
        with patch("main.supabase") as mock_sb:
            mock_sb.storage.from_.return_value.list.side_effect = Exception("storage error")
            resp = client.get("/documents")
        assert resp.status_code == 200
        assert resp.json()["files"] == []


# ---------------------------------------------------------------------------
# DELETE /documents/{filename}
# ---------------------------------------------------------------------------

class TestDeleteDocument:
    def test_returns_ok(self, client):
        with patch("main.supabase") as mock_sb:
            with patch("main.delete_file_chunks"):
                mock_sb.storage.from_.return_value.remove.return_value = MagicMock()
                resp = client.delete("/documents/nvidia10k.pdf")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# GET /portfolio/{user_id}
# ---------------------------------------------------------------------------

class TestGetPortfolio:
    def test_returns_empty_portfolio_for_unknown_user(self, client):
        with patch("main.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            resp = client.get("/portfolio/unknown_user")
        assert resp.status_code == 200
        data = resp.json()
        assert data["positions"] == []
        assert data["total_value"] == 0
        assert data["total_pl"] == 0

    def test_returns_position_data(self, client):
        rows = [{"id": "row-1", "ticker": "AAPL", "shares": 10, "avg_buy_price": 150.0}]
        with patch("main.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
            with patch("yfinance.Ticker") as mock_ticker_cls:
                mock_t = MagicMock()
                import pandas as pd, numpy as np
                dates = pd.date_range("2024-01-01", periods=5, freq="B")
                mock_t.history.return_value = pd.DataFrame(
                    {"Close": np.linspace(180, 185, 5)}, index=dates
                )
                mock_t.info = {"shortName": "Apple Inc."}
                mock_ticker_cls.return_value = mock_t
                resp = client.get("/portfolio/user_abc")

        assert resp.status_code == 200
        positions = resp.json()["positions"]
        assert len(positions) == 1
        assert positions[0]["ticker"] == "AAPL"
        assert positions[0]["shares"] == 10.0
        assert positions[0]["current_price"] > 0


# ---------------------------------------------------------------------------
# POST /portfolio  and  DELETE /portfolio/{user_id}/{ticker}
# ---------------------------------------------------------------------------

class TestPortfolioMutations:
    def test_add_position_returns_ok(self, client):
        with patch("main.supabase") as mock_sb:
            mock_sb.table.return_value.upsert.return_value.execute.return_value = MagicMock()
            resp = client.post("/portfolio", json={
                "user_id": "user_abc",
                "ticker": "aapl",
                "shares": 5.0,
                "avg_buy_price": 170.0,
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_add_position_uppercases_ticker(self, client):
        with patch("main.supabase") as mock_sb:
            upsert_mock = mock_sb.table.return_value.upsert
            upsert_mock.return_value.execute.return_value = MagicMock()
            client.post("/portfolio", json={
                "user_id": "user_abc", "ticker": "msft",
                "shares": 3.0, "avg_buy_price": 300.0,
            })
            call_data = upsert_mock.call_args[0][0]
        assert call_data["ticker"] == "MSFT"

    def test_remove_position_returns_ok(self, client):
        with patch("main.supabase") as mock_sb:
            (mock_sb.table.return_value.delete.return_value
                     .eq.return_value.eq.return_value
                     .execute.return_value) = MagicMock()
            resp = client.delete("/portfolio/user_abc/AAPL")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
