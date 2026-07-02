"""API smoke tests. External services are monkeypatched; the DB goes to tmp."""

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.services import edgar

from tests.test_normalize import SUBMISSIONS, clean_facts

client = TestClient(app)


DCF_BODY = {
    "ticker": "TEST",
    "base_revenue": 1000,
    "base_margin": 0.20,
    "target_margin": 0.20,
    "tax_rate": 0.25,
    "sales_to_capital": 2.0,
    "growth_stage1": 0.05,
    "terminal_growth": 0.02,
    "wacc_override": 0.08,
    "total_debt": 500,
    "cash": 200,
    "diluted_shares": 100,
    "current_price": 50,
}


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite3")


class TestCompanyEndpoint:
    @pytest.fixture(autouse=True)
    def mock_edgar(self, monkeypatch):
        monkeypatch.setattr(edgar, "resolve_cik", lambda t, force_refresh=False: "0000000001")
        monkeypatch.setattr(edgar, "get_company_facts", lambda c, force_refresh=False: clean_facts())
        monkeypatch.setattr(edgar, "get_submissions", lambda c, force_refresh=False: SUBMISSIONS)

    def test_company_payload(self):
        response = client.get("/api/company/test")
        assert response.status_code == 200
        body = response.json()
        assert body["ticker"] == "TEST"
        assert body["company_name"] == "Test Corp"
        assert len(body["years"]) == 3
        assert body["derived"]["latest_revenue"] == 1000.0

    def test_unknown_ticker_404(self, monkeypatch):
        def boom(t, force_refresh=False):
            raise edgar.EdgarError(f"Ticker '{t.upper()}' not found in SEC company list")

        monkeypatch.setattr(edgar, "resolve_cik", boom)
        response = client.get("/api/company/zzzz")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestDcfEndpoint:
    def test_run(self):
        response = client.post("/api/dcf", json=DCF_BODY)
        assert response.status_code == 200
        body = response.json()
        assert body["intrinsic_per_share"] > 0
        assert len(body["years"]) == 10
        assert len(body["sensitivity"]["matrix"]) == 5

    def test_model_error_is_422(self):
        response = client.post("/api/dcf", json={**DCF_BODY, "terminal_growth": 0.09})
        assert response.status_code == 422
        assert "terminal growth" in response.json()["detail"]

    def test_schema_error_is_422(self):
        response = client.post("/api/dcf", json={**DCF_BODY, "diluted_shares": 0})
        assert response.status_code == 422


class TestValuationsCrud:
    def test_save_list_get_delete(self):
        run = client.post("/api/dcf", json=DCF_BODY).json()
        saved = client.post(
            "/api/valuations",
            json={
                "ticker": "TEST",
                "company_name": "Test Corp",
                "price_at_run": 50.0,
                "inputs": DCF_BODY,
                "result": run,
            },
        )
        assert saved.status_code == 200
        vid = saved.json()["id"]
        assert vid is not None

        listed = client.get("/api/valuations").json()
        assert len(listed) == 1
        assert listed[0]["ticker"] == "TEST"

        one = client.get(f"/api/valuations/{vid}")
        assert one.status_code == 200
        assert one.json()["result"]["intrinsic_per_share"] == pytest.approx(
            run["intrinsic_per_share"]
        )

        assert client.delete(f"/api/valuations/{vid}").status_code == 200
        assert client.get(f"/api/valuations/{vid}").status_code == 404
        assert client.delete(f"/api/valuations/{vid}").status_code == 404
