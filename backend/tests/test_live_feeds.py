import pytest
import asyncio
from backend.data.live_feeds import fetch_weather, fetch_aqi, fetch_traffic, fetch_city_pulse

@pytest.mark.asyncio
async def test_fetch_weather_simulation():
    data, src = await fetch_weather("TestCity")
    assert src in ("live", "simulated")
    assert data.temperature > 0
    assert data.humidity >= 0

@pytest.mark.asyncio
async def test_fetch_aqi_simulation():
    data, src = await fetch_aqi("TestCity")
    assert src in ("live", "simulated")
    assert data.aqi > 0

@pytest.mark.asyncio
async def test_fetch_city_pulse():
    pulse = await fetch_city_pulse("TestCity")
    assert pulse.city == "TestCity"
    assert pulse.overall_health_score >= 0
    assert pulse.overall_health_score <= 100
