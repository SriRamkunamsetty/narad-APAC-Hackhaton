"""
Tests for backend/data/live_feeds.py — verifies the simulation fallback
paths work correctly and that data_sources labeling is honest (never
claims "live" when it's actually simulated).
"""
import pytest

from backend.data.live_feeds import fetch_weather, fetch_aqi, fetch_traffic, fetch_city_pulse


class TestSimulationFallback:
    """With no API keys configured (the test environment default), every
    fetch must fall back to simulation and label itself honestly."""

    async def test_weather_falls_back_to_simulation(self):
        data, source = await fetch_weather("Hyderabad")
        assert source == "simulated"
        assert -10 <= data.temperature <= 50  # sane physical range

    async def test_aqi_falls_back_to_simulation(self):
        data, source = await fetch_aqi("Hyderabad")
        assert source == "simulated"
        assert 0 <= data.aqi <= 500

    async def test_traffic_falls_back_to_simulation(self):
        data, source = await fetch_traffic("Hyderabad")
        assert source == "simulated"
        assert 0 <= data.congestion_level <= 100

    async def test_city_pulse_reports_honest_sources(self):
        pulse = await fetch_city_pulse("Hyderabad")
        # Hospitals/safety/economy are ALWAYS simulated (no public API exists)
        assert pulse.data_sources["hospitals"] in ("simulated", "manual")
        assert pulse.data_sources["safety"] == "simulated"
        assert pulse.data_sources["economy"] == "simulated"

    async def test_city_pulse_has_valid_health_score(self):
        pulse = await fetch_city_pulse("Hyderabad")
        assert 0 <= pulse.overall_health_score <= 100

    async def test_city_pulse_never_crashes_on_repeated_calls(self):
        """Basic resilience check — repeated calls shouldn't accumulate state incorrectly"""
        for _ in range(3):
            pulse = await fetch_city_pulse("Hyderabad")
            assert pulse.city == "Hyderabad"
