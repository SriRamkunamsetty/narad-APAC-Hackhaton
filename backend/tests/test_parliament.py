import pytest
from backend.agents.parliament import _extract_json, _fallback_stance
from backend.models.schemas import AgentName, CityPulse, WeatherData, AQIData, TrafficData, HospitalData, SafetyData, EconomyData
from datetime import datetime, timezone

def test_extract_json():
    text = "```json\n{\"vote\": \"approve\"}\n```"
    data = _extract_json(text)
    assert data.get("vote") == "approve"

    text2 = "Some prefix\n{\"vote\": \"escalate\"}\nSome suffix"
    data2 = _extract_json(text2)
    assert data2.get("vote") == "escalate"

def test_fallback_stance():
    pulse = CityPulse(
        city="Test",
        timestamp=datetime.now(timezone.utc),
        weather=WeatherData(temperature=30, humidity=50, wind_speed=10, wind_direction="N", condition="Clear", feels_like=32, visibility=10, pressure=1010),
        aqi=AQIData(aqi=50, status="Good", pm25=10, pm10=20, no2=10, o3=10, co=0.5, so2=5, color="green"),
        traffic=TrafficData(congestion_level=10, avg_speed_kmh=40, incidents=0, affected_zones=[], travel_time_index=1.0, hotspots=[]),
        hospitals=HospitalData(total_hospitals=10, available_beds=100, icu_available=10, ambulances_active=5, emergency_wait_minutes=10, capacity_percent=50, critical_facilities=[], manual_reports_count=0, manual_coverage_pct=0),
        safety=SafetyData(active_incidents=1, emergency_calls_1h=5, police_response_minutes=10, fire_units_deployed=1, high_risk_zones=[], alert_level="Green"),
        economy=EconomyData(fuel_price_litre=100, essential_goods_index=100, market_activity="Active", utility_load_percent=50, water_supply_status="Normal", power_outages=0),
        overall_health_score=90,
        alerts=[],
        data_sources={}
    )
    stance = _fallback_stance(AgentName.TRANSPORT, "🚦", pulse)
    assert stance.vote.value == "approve"
