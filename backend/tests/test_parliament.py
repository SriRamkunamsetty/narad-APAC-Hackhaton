"""
Tests for backend/agents/parliament.py — including a regression test for
the ADK session memory leak found and fixed today (sessions were created
per agent call but never deleted, growing unbounded on a long-running
instance).
"""
import pytest

from backend.agents.parliament import run_parliament_session, _session_service
from backend.data.live_feeds import fetch_city_pulse


async def _count_sessions():
    result = await _session_service.list_sessions(app_name="narad_parliament", user_id="narad_system")
    return len(result.sessions) if hasattr(result, "sessions") else len(result)


class TestSessionCleanup:
    """Regression coverage for the memory leak: InMemorySessionService.delete_session
    exists in the ADK library but was never called anywhere in the original code."""

    async def test_no_session_leak_after_single_run(self):
        pulse = await fetch_city_pulse("Hyderabad")
        before = await _count_sessions()
        await run_parliament_session(pulse, "Test trigger")
        after = await _count_sessions()
        assert after == before, "Sessions must be cleaned up after each parliament run"

    async def test_no_session_leak_after_multiple_runs(self):
        pulse = await fetch_city_pulse("Hyderabad")
        await run_parliament_session(pulse, "Run 1")
        await run_parliament_session(pulse, "Run 2")
        await run_parliament_session(pulse, "Run 3")
        assert await _count_sessions() == 0


class TestParliamentDecision:
    async def test_produces_five_agent_stances(self):
        pulse = await fetch_city_pulse("Hyderabad")
        decision = await run_parliament_session(pulse, "Test")
        assert len(decision.stances) == 5

    async def test_all_agents_represented(self):
        pulse = await fetch_city_pulse("Hyderabad")
        decision = await run_parliament_session(pulse, "Test")
        agent_names = {s.agent.value for s in decision.stances}
        assert agent_names == {
            "TransportAgent", "HealthAgent", "EnvironmentAgent", "EconomyAgent", "SafetyAgent"
        }

    async def test_decision_has_consensus_and_causal_chain(self):
        pulse = await fetch_city_pulse("Hyderabad")
        decision = await run_parliament_session(pulse, "Test")
        assert decision.consensus
        assert isinstance(decision.causal_chain, list)
        assert isinstance(decision.dissent_log, list)

    async def test_falls_back_gracefully_without_gemini_key(self):
        """With no GEMINI_API_KEY (the test environment default), agents
        should use the rule-based fallback rather than crashing."""
        pulse = await fetch_city_pulse("Hyderabad")
        decision = await run_parliament_session(pulse, "Test")
        # Every stance should still be a valid, well-formed AgentStance
        for stance in decision.stances:
            assert stance.confidence >= 0
            assert stance.vote is not None
