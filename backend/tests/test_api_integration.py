import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_api_info(client):
    response = client.get("/api/info")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"

def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_manual_hospital_report_unauthorized(client):
    response = client.post("/api/manual-data/hospital", json={
        "hospital_name": "Test Hospital",
        "available_beds": 10,
        "icu_available": 2,
        "ambulances_active": 1,
        "emergency_wait_minutes": 15,
        "reported_by": "Staff"
    })
    # Should be 401 because no API key
    assert response.status_code == 401
