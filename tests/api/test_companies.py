import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_list_companies_count():
    response = client.get("/api/v1/companies")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 92
    assert len(data["companies"]) == 92


def test_get_company_profile_valid():
    response = client.get("/api/v1/companies/TCS")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "TCS"
    assert "Tata Consultancy Services" in data["company_name"]
    assert "latest_kpis" in data


def test_get_company_profile_invalid():
    response = client.get("/api/v1/companies/INVALID_TICKER_999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_company_pl():
    response = client.get("/api/v1/companies/INFY/pl")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "INFY"
    assert len(data["pl"]) >= 5


def test_get_company_tearsheet_pdf():
    response = client.get("/api/v1/companies/TCS/tearsheet")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 30 * 1024
