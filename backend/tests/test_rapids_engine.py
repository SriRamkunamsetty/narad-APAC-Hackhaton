"""
Tests for backend/data/rapids_engine.py — including a regression test for
the percentile-ordering bug found and fixed earlier in this project
(percentiles were computed from unsorted arrays, producing non-monotonic
values).
"""
import pytest

from backend.data.rapids_engine import (
    run_scenario_simulations, evaluate_scenario, run_benchmark, detect_anomalies
)
from backend.models.schemas import ScenarioRequest


class TestScenarioSimulation:
    def test_percentiles_are_monotonically_increasing(self):
        """Regression test: percentiles must be sorted, not just indexed
        into an unsorted random array (the original bug)."""
        scenario = ScenarioRequest(
            name="Test", description="Test",
            parameters={"traffic_delta": 20, "health_delta": 5, "aqi_delta": 10, "safety_delta": 2},
            scenario_count=1000
        )
        city_state = {"congestion": 45, "hospital_load": 60, "aqi": 120, "incidents": 5}
        outcomes, _, _ = run_scenario_simulations(scenario, city_state)

        traffic_values = [o["traffic"] for o in outcomes]
        assert traffic_values == sorted(traffic_values), \
            "Percentiles must be monotonically increasing — this is the exact bug found earlier"

    def test_five_percentiles_returned(self):
        scenario = ScenarioRequest(
            name="Test", description="Test", parameters={}, scenario_count=500
        )
        city_state = {"congestion": 50, "hospital_load": 50, "aqi": 100, "incidents": 3}
        outcomes, _, _ = run_scenario_simulations(scenario, city_state)
        assert len(outcomes) == 5
        assert [o["percentile"] for o in outcomes] == [10, 25, 50, 75, 90]

    def test_values_stay_within_physical_bounds(self):
        """Traffic congestion should never go negative or exceed 100%"""
        scenario = ScenarioRequest(
            name="Extreme", description="Extreme scenario",
            parameters={"traffic_delta": 1000}, scenario_count=500
        )
        city_state = {"congestion": 50, "hospital_load": 50, "aqi": 100, "incidents": 3}
        outcomes, _, _ = run_scenario_simulations(scenario, city_state)
        for o in outcomes:
            assert 0 <= o["traffic"] <= 100
            assert 0 <= o["health_load"] <= 100

    async def test_evaluate_scenario_produces_recommendation(self):
        scenario = ScenarioRequest(
            name="Test", description="Test",
            parameters={"traffic_delta": 20, "health_delta": 5, "aqi_delta": 10, "safety_delta": 2},
            scenario_count=500
        )
        city_state = {"congestion": 45, "hospital_load": 60, "aqi": 120, "incidents": 5}
        outcome = await evaluate_scenario(scenario, city_state)

        assert outcome.recommendation
        assert 0 <= outcome.confidence <= 1
        assert outcome.processing_ms > 0


class TestBenchmark:
    async def test_benchmark_returns_valid_comparison(self):
        result = await run_benchmark(dataset_size=10_000)
        assert result.pandas_time_ms > 0
        assert result.dataset_size == 10_000
        assert result.speedup is not None and result.speedup > 0

    async def test_benchmark_respects_dataset_size(self):
        small = await run_benchmark(dataset_size=5_000)
        assert small.dataset_size == 5_000


class TestAnomalyDetection:
    def test_no_anomaly_in_stable_data(self):
        history = [
            {"aqi": 100, "congestion": 50, "hospital_load": 60, "incidents": 5}
            for _ in range(15)
        ]
        anomalies = detect_anomalies(history)
        assert anomalies == []

    def test_detects_sudden_spike(self):
        history = [
            {"aqi": 100, "congestion": 50, "hospital_load": 60, "incidents": 5}
            for _ in range(15)
        ]
        history.append({"aqi": 450, "congestion": 50, "hospital_load": 60, "incidents": 5})
        anomalies = detect_anomalies(history)
        assert any("aqi" in a.lower() for a in anomalies)

    def test_insufficient_history_returns_empty(self):
        history = [{"aqi": 100, "congestion": 50, "hospital_load": 60, "incidents": 5}] * 3
        assert detect_anomalies(history) == []
