import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_screener_min_roe_filter():
    response = client.get("/api/v1/screener?min_roe=15.0")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    for comp in data["results"]:
        assert comp["roe"] >= 15.0


def test_screener_invalid_param_400():
    response = client.get("/api/v1/screener?max_pe=-10.0")
    assert response.status_code == 400
    data = response.json()
    assert "cannot be negative" in data["detail"].lower()
