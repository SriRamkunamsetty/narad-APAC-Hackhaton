import pytest
from backend.data.rapids_engine import detect_anomalies

def test_detect_anomalies():
    history = [
        {"aqi": 50, "congestion": 50, "hospital_load": 50, "incidents": 2},
        {"aqi": 55, "congestion": 52, "hospital_load": 49, "incidents": 3},
        {"aqi": 300, "congestion": 95, "hospital_load": 90, "incidents": 15}, # Spike
    ]
    anomalies = detect_anomalies(history)
    assert len(anomalies) > 0
    assert any("AQI" in a for a in anomalies)
