import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_list_sectors_count():
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 10
    assert len(data["sectors"]) >= 10


def test_get_sector_companies_valid():
    response = client.get("/api/v1/sectors/Information%20Technology/companies")
    assert response.status_code == 200
    data = response.json()
    assert data["sector"] == "Information Technology"
    assert data["count"] >= 5


def test_get_sector_companies_invalid():
    response = client.get("/api/v1/sectors/NonExistentSector/companies")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
