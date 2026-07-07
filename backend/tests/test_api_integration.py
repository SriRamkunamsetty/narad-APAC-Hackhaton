"""
Integration tests for the FastAPI app itself — exercises the real HTTP
layer (routing, dependency injection, middleware) rather than just calling
internal functions directly. This is what would have caught the WebSocket
auth bypass if it had existed on a REST endpoint instead.
"""
import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from backend import config
    monkeypatch.setattr(config, "NARAD_ADMIN_API_KEY", "test-integration-key")
    from backend import main
    return TestClient(main.app)


class TestHealthAndDiagnostics:
    def test_health_endpoint_responds(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert "checks" in body

    def test_diagnostics_llm_reports_status(self, client):
        r = client.get("/api/diagnostics/llm")
        assert r.status_code == 200
        assert "live_call_success" in r.json()

    def test_diagnostics_bigquery_reports_status(self, client):
        r = client.get("/api/diagnostics/bigquery")
        assert r.status_code == 200
        assert "available" in r.json()

    def test_security_headers_present(self, client):
        r = client.get("/api/health")
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"
        assert "strict-transport-security" in r.headers
        assert "x-request-id" in r.headers


class TestWriteEndpointAuth:
    """The core security property: writes must be rejected without a valid key"""

    def test_hospital_report_rejected_without_key(self, client):
        r = client.post("/api/manual-data/hospital", json={
            "hospital_name": "Test", "available_beds": 10, "icu_available": 1
        })
        assert r.status_code == 401

    def test_hospital_report_rejected_with_wrong_key(self, client):
        r = client.post(
            "/api/manual-data/hospital",
            json={"hospital_name": "Test", "available_beds": 10, "icu_available": 1},
            headers={"X-API-Key": "wrong-key"}
        )
        assert r.status_code == 401

    def test_hospital_report_accepted_with_correct_key(self, client):
        r = client.post(
            "/api/manual-data/hospital",
            json={"hospital_name": "Integration Test Hospital", "available_beds": 10, "icu_available": 1},
            headers={"X-API-Key": "test-integration-key"}
        )
        assert r.status_code == 200
        # Clean up
        client.delete(
            "/api/manual-data/hospital/Integration Test Hospital",
            headers={"X-API-Key": "test-integration-key"}
        )

    def test_hospital_report_negative_beds_rejected(self, client):
        r = client.post(
            "/api/manual-data/hospital",
            json={"hospital_name": "Test", "available_beds": -5, "icu_available": 1},
            headers={"X-API-Key": "test-integration-key"}
        )
        assert r.status_code == 422

    def test_parliament_trigger_rejected_without_key(self, client):
        r = client.post("/api/parliament/trigger?reason=test")
        assert r.status_code == 401

    def test_read_endpoints_work_without_key(self, client):
        """Read-only endpoints must remain publicly accessible — only writes require auth"""
        r = client.get("/api/manual-data/hospital")
        assert r.status_code == 200


class TestInputValidationAtHttpLayer:
    def test_ask_endpoint_rejects_empty_question(self, client):
        r = client.post("/api/ask", json={"question": "", "language": "english"})
        assert r.status_code == 422

    def test_ask_endpoint_rejects_invalid_language(self, client):
        r = client.post("/api/ask", json={"question": "test", "language": "klingon"})
        assert r.status_code in (400, 422)

    def test_scenario_simulate_rejects_excessive_count(self, client):
        r = client.post("/api/scenario/simulate", json={
            "name": "Test", "description": "Test",
            "parameters": {}, "scenario_count": 999999
        })
        assert r.status_code == 422
