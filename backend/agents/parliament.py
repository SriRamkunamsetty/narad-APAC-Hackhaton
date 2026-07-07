"""
NARAD - The Agent Parliament Orchestrator
This is the heart of NARAD: 5 specialized ADK agents independently analyze
live city data, vote on recommended actions, and a synthesis layer produces
a consensus decision — logging every point of disagreement transparently.
"""
import asyncio
import time
import uuid
import logging
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from backend.agents.specialized_agents import (
    build_transport_agent, build_health_agent, build_environment_agent,
    build_economy_agent, build_safety_agent
)
from backend.models.schemas import (
    AgentName, AgentStance, ParliamentDecision, VoteDecision, Severity, CityPulse
)
from backend.config import GEMINI_MODEL, GEMINI_API_KEY

logger = logging.getLogger("narad.parliament")

# ─── Agent Registry ────────────────────────────────────────────────────────────

_AGENTS = {
    AgentName.TRANSPORT:   {"builder": build_transport_agent,   "emoji": "🚦"},
    AgentName.HEALTH:      {"builder": build_health_agent,      "emoji": "🏥"},
    AgentName.ENVIRONMENT: {"builder": build_environment_agent, "emoji": "🌫️"},
    AgentName.ECONOMY:     {"builder": build_economy_agent,     "emoji": "⚡"},
    AgentName.SAFETY:      {"builder": build_safety_agent,      "emoji": "🚔"},
}

_session_service = InMemorySessionService()

# Hard ceiling on a single agent's Gemini call. Without this, a hung API
# call blocks the entire parliament session indefinitely (asyncio.gather
# waits for every task, including a stuck one).
AGENT_TIMEOUT_SECONDS = 20
_agent_instances: Dict[str, Any] = {}
_runners: Dict[str, Runner] = {}


def _get_runner(agent_name: str) -> Runner:
    """Lazily build and cache agent + runner instances"""
    if agent_name not in _runners:
        builder = _AGENTS[AgentName(agent_name)]["builder"]
        agent = builder()
        _agent_instances[agent_name] = agent
        _runners[agent_name] = Runner(
            agent=agent,
            app_name="narad_parliament",
            session_service=_session_service
        )
    return _runners[agent_name]


def _build_agent_prompt(agent_name: AgentName, pulse: CityPulse, trigger: str) -> str:
    """Build a domain-specific prompt with live city data for each agent"""

    base_context = f"""LIVE CITY DATA SNAPSHOT — {pulse.city} — {pulse.timestamp.strftime('%Y-%m-%d %H:%M UTC')}
Trigger event: {trigger}

WEATHER: {pulse.weather.temperature:.1f}°C, {pulse.weather.condition}, humidity {pulse.weather.humidity:.0f}%, wind {pulse.weather.wind_speed:.1f}km/h {pulse.weather.wind_direction}
AIR QUALITY: AQI {pulse.aqi.aqi} ({pulse.aqi.status}), PM2.5 {pulse.aqi.pm25:.1f}μg/m³, PM10 {pulse.aqi.pm10:.1f}μg/m³, NO2 {pulse.aqi.no2:.1f}μg/m³
TRAFFIC: {pulse.traffic.congestion_level:.0f}% congestion, avg speed {pulse.traffic.avg_speed_kmh:.0f}km/h, {pulse.traffic.incidents} incidents, affected: {', '.join(pulse.traffic.affected_zones) if pulse.traffic.affected_zones else 'none'}
HOSPITALS: {pulse.hospitals.capacity_percent:.0f}% capacity, {pulse.hospitals.available_beds} beds available, {pulse.hospitals.icu_available} ICU beds, {pulse.hospitals.ambulances_active} ambulances active, {pulse.hospitals.emergency_wait_minutes:.0f}min ER wait
SAFETY: {pulse.safety.active_incidents} active incidents, {pulse.safety.emergency_calls_1h} emergency calls/hr, {pulse.safety.police_response_minutes:.0f}min response time, alert level {pulse.safety.alert_level}
ECONOMY: {pulse.economy.utility_load_percent:.0f}% grid load, {pulse.economy.power_outages} zones with outages, fuel ₹{pulse.economy.fuel_price_litre:.2f}/L, water supply: {pulse.economy.water_supply_status}
OVERALL CITY HEALTH SCORE: {pulse.overall_health_score:.0f}/100
"""

    tool_call_instructions = {
        AgentName.TRANSPORT: (
            f"Call analyze_traffic_conditions with: congestion_level={pulse.traffic.congestion_level}, "
            f"avg_speed_kmh={pulse.traffic.avg_speed_kmh}, incidents={pulse.traffic.incidents}, "
            f"affected_zones=\"{', '.join(pulse.traffic.affected_zones)}\", "
            f"travel_time_index={pulse.traffic.travel_time_index}"
        ),
        AgentName.HEALTH: (
            f"Call analyze_health_capacity with: available_beds={pulse.hospitals.available_beds}, "
            f"icu_available={pulse.hospitals.icu_available}, capacity_percent={pulse.hospitals.capacity_percent}, "
            f"ambulances_active={pulse.hospitals.ambulances_active}, "
            f"emergency_wait_minutes={pulse.hospitals.emergency_wait_minutes}, "
            f"critical_facilities=\"{', '.join(pulse.hospitals.critical_facilities)}\""
        ),
        AgentName.ENVIRONMENT: (
            f"Call analyze_environment with: aqi={pulse.aqi.aqi}, pm25={pulse.aqi.pm25}, pm10={pulse.aqi.pm10}, "
            f"no2={pulse.aqi.no2}, temperature={pulse.weather.temperature}, humidity={pulse.weather.humidity}, "
            f"wind_speed={pulse.weather.wind_speed}"
        ),
        AgentName.ECONOMY: (
            f"Call analyze_economy_resources with: utility_load_percent={pulse.economy.utility_load_percent}, "
            f"power_outages={pulse.economy.power_outages}, fuel_price_litre={pulse.economy.fuel_price_litre}, "
            f"essential_goods_index={pulse.economy.essential_goods_index}, "
            f"market_activity=\"{pulse.economy.market_activity}\", "
            f"water_supply_status=\"{pulse.economy.water_supply_status}\""
        ),
        AgentName.SAFETY: (
            f"Call analyze_public_safety with: active_incidents={pulse.safety.active_incidents}, "
            f"emergency_calls_1h={pulse.safety.emergency_calls_1h}, "
            f"police_response_minutes={pulse.safety.police_response_minutes}, "
            f"fire_units_deployed={pulse.safety.fire_units_deployed}, "
            f"high_risk_zones=\"{', '.join(pulse.safety.high_risk_zones)}\", "
            f"alert_level=\"{pulse.safety.alert_level}\""
        ),
    }

    instruction = f"""{base_context}

TASK: {tool_call_instructions[agent_name]}

Then, based on the tool's output, respond in this EXACT JSON format (no markdown, no extra text):
{{
  "analysis": "2-3 sentence analysis of the situation from your domain expertise",
  "recommendation": "1-2 sentence specific, actionable recommendation",
  "confidence": 0.85,
  "vote": "approve|reject|abstain|escalate",
  "urgency": "low|moderate|high|critical",
  "key_metrics": {{"metric_name": "value"}},
  "dissent_reason": null
}}

Vote "approve" if current conditions are manageable with standard operations.
Vote "escalate" if this requires immediate cross-department coordination.
Vote "reject" if you disagree with the premise that action is needed right now.
Vote "abstain" only if data is insufficient for your domain.
Set dissent_reason if your assessment conflicts with what other city departments might prioritize (e.g. Health wants school closure but Economy worries about disruption cost)."""

    return instruction


async def _run_single_agent(agent_name: AgentName, pulse: CityPulse, trigger: str) -> AgentStance:
    """Run one agent and parse its structured stance"""
    emoji = _AGENTS[agent_name]["emoji"]
    t0 = time.time()

    user_id = "narad_system"
    session_id = f"session_{agent_name.value}_{uuid.uuid4().hex[:8]}"

    try:
        runner = _get_runner(agent_name.value)
        prompt = _build_agent_prompt(agent_name, pulse, trigger)

        await _session_service.create_session(
            app_name="narad_parliament", user_id=user_id, session_id=session_id
        )

        content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

        final_text = ""

        async def _consume_stream():
            nonlocal final_text
            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=content
            ):
                if hasattr(event, "content") and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_text += part.text

        # Hard timeout — without this, a hung Gemini call hangs the whole
        # parliament session (all 5 agents run concurrently, but a single
        # stuck agent still blocks asyncio.gather from ever returning).
        await asyncio.wait_for(_consume_stream(), timeout=AGENT_TIMEOUT_SECONDS)

        parsed = _extract_json(final_text)

        stance = AgentStance(
            agent=agent_name,
            emoji=emoji,
            analysis=parsed.get("analysis", "Analysis unavailable"),
            recommendation=parsed.get("recommendation", "No specific recommendation"),
            confidence=float(parsed.get("confidence", 0.7)),
            vote=VoteDecision(parsed.get("vote", "approve")),
            urgency=Severity(parsed.get("urgency", "moderate")),
            key_metrics=parsed.get("key_metrics", {}),
            dissent_reason=parsed.get("dissent_reason")
        )
        logger.info(f"{emoji} {agent_name.value} voted {stance.vote.value} "
                     f"({(time.time()-t0)*1000:.0f}ms)")
        return stance

    except asyncio.TimeoutError:
        logger.error(f"⏱️  Agent {agent_name.value} timed out after {AGENT_TIMEOUT_SECONDS}s — "
                     f"falling back to rule-based decision")
        return _fallback_stance(agent_name, emoji, pulse)

    except Exception as e:
        logger.exception(f"❌ Agent {agent_name.value} failed — falling back to rule-based decision. "
                          f"Root cause: {type(e).__name__}: {e}")
        return _fallback_stance(agent_name, emoji, pulse)

    finally:
        # ALWAYS clean up the session, whether the call succeeded, failed, or
        # timed out. Without this, every session leaks — confirmed via
        # InMemorySessionService.delete_session existing but never being
        # called anywhere in the original code. At one parliament session per
        # minute running indefinitely, this previously grew memory until the
        # instance restarted.
        try:
            await _session_service.delete_session(
                app_name="narad_parliament", user_id=user_id, session_id=session_id
            )
        except Exception as cleanup_error:
            logger.warning(f"Session cleanup failed for {session_id} (non-fatal): {cleanup_error}")


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM response, handling markdown code fences"""
    text = text.strip()
    # Remove markdown fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object within text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


def _fallback_stance(agent_name: AgentName, emoji: str, pulse: CityPulse) -> AgentStance:
    """Rule-based fallback if LLM call fails — ensures system never crashes"""
    rules = {
        AgentName.TRANSPORT: (pulse.traffic.congestion_level > 70, pulse.traffic.congestion_level),
        AgentName.HEALTH: (pulse.hospitals.capacity_percent > 80, pulse.hospitals.capacity_percent),
        AgentName.ENVIRONMENT: (pulse.aqi.aqi > 150, pulse.aqi.aqi / 3),
        AgentName.ECONOMY: (pulse.economy.utility_load_percent > 85, pulse.economy.utility_load_percent),
        AgentName.SAFETY: (pulse.safety.active_incidents > 8, pulse.safety.active_incidents * 8),
    }
    is_urgent, score = rules.get(agent_name, (False, 50))
    return AgentStance(
        agent=agent_name, emoji=emoji,
        analysis=f"Automated fallback analysis: metric score {score:.0f} for {agent_name.value}.",
        recommendation="Continue standard monitoring protocols" if not is_urgent else "Escalate for manual review",
        confidence=0.5,
        vote=VoteDecision.ESCALATE if is_urgent else VoteDecision.APPROVE,
        urgency=Severity.HIGH if is_urgent else Severity.LOW,
        key_metrics={"fallback_score": score},
        dissent_reason="Fallback mode: LLM unavailable, rule-based decision used"
    )


def _build_causal_chain(pulse: CityPulse, stances: List[AgentStance]) -> List[str]:
    """Construct a causal reasoning chain across domains"""
    chain = []

    if pulse.aqi.aqi > 150 and pulse.traffic.congestion_level > 60:
        chain.append(f"High traffic congestion ({pulse.traffic.congestion_level:.0f}%) → increased vehicular "
                       f"emissions → elevated AQI ({pulse.aqi.aqi})")
    if pulse.aqi.aqi > 150:
        chain.append(f"AQI {pulse.aqi.aqi} ({pulse.aqi.status}) → respiratory distress in sensitive groups "
                       f"→ projected {'+8-15%' if pulse.aqi.aqi > 200 else '+3-8%'} rise in ER visits within 6 hours")
    if pulse.hospitals.capacity_percent > 75:
        chain.append(f"Hospital capacity at {pulse.hospitals.capacity_percent:.0f}% → reduced surge buffer "
                       f"→ risk of patient diversion if incidents spike")
    if pulse.safety.active_incidents > 6 and pulse.traffic.congestion_level > 60:
        chain.append(f"Traffic congestion → delayed emergency response "
                       f"(current: {pulse.safety.police_response_minutes:.0f}min) → compounds safety risk")
    if pulse.economy.power_outages > 1:
        chain.append(f"Grid load {pulse.economy.utility_load_percent:.0f}% → power outages in "
                       f"{pulse.economy.power_outages} zones → water pumping stations at risk → supply disruption")

    if not chain:
        chain.append("No significant cross-domain causal risks detected — city systems operating independently within normal parameters")

    return chain


def _synthesize_consensus(pulse: CityPulse, stances: List[AgentStance]) -> Dict[str, Any]:
    """
    Synthesize the 5 agent stances into a unified decision.
    This is the 'parliament vote counting' logic.
    """
    votes = [s.vote for s in stances]
    escalate_count = votes.count(VoteDecision.ESCALATE)
    reject_count = votes.count(VoteDecision.REJECT)
    approve_count = votes.count(VoteDecision.APPROVE)

    urgency_rank = {Severity.LOW: 0, Severity.MODERATE: 1, Severity.HIGH: 2, Severity.CRITICAL: 3}
    max_urgency = max(stances, key=lambda s: urgency_rank[s.urgency]).urgency

    avg_confidence = sum(s.confidence for s in stances) / len(stances)

    # Dissent detection: agents whose urgency differs sharply from the mean
    dissent_log = []
    for s in stances:
        if s.dissent_reason:
            dissent_log.append(f"{s.emoji} {s.agent.value}: {s.dissent_reason}")

    urgencies = [urgency_rank[s.urgency] for s in stances]
    if max(urgencies) - min(urgencies) >= 2:
        high_agents = [s.agent.value for s in stances if urgency_rank[s.urgency] == max(urgencies)]
        low_agents  = [s.agent.value for s in stances if urgency_rank[s.urgency] == min(urgencies)]
        dissent_log.append(
            f"⚡ Urgency split: {', '.join(high_agents)} see {max_urgency.value} urgency while "
            f"{', '.join(low_agents)} assess the situation as routine"
        )

    # Build consensus statement
    if escalate_count >= 2:
        consensus = (
            f"PARLIAMENT CONSENSUS: {escalate_count}/5 agents recommend escalation. "
            f"Cross-domain coordination required — this is not a single-department issue."
        )
    elif escalate_count == 1 or reject_count >= 2:
        consensus = (
            f"PARLIAMENT SPLIT DECISION: Mixed signals across domains. "
            f"Recommend targeted intervention in flagged areas while monitoring others."
        )
    else:
        consensus = (
            f"PARLIAMENT CONSENSUS: {approve_count}/5 agents confirm conditions are within "
            f"manageable parameters. Standard operations continue."
        )

    # Build action plan (ordered by urgency)
    sorted_stances = sorted(stances, key=lambda s: urgency_rank[s.urgency], reverse=True)
    action_plan = [f"{s.emoji} [{s.agent.value}] {s.recommendation}" for s in sorted_stances
                   if s.vote in (VoteDecision.ESCALATE, VoteDecision.APPROVE)]

    affected_zones = list(set(pulse.traffic.affected_zones + pulse.safety.high_risk_zones))

    impact = "LOW"
    if max_urgency == Severity.CRITICAL:
        impact = f"~{len(affected_zones) * 50000:,} residents directly affected, immediate action required"
    elif max_urgency == Severity.HIGH:
        impact = f"~{len(affected_zones) * 20000:,} residents in affected zones, action needed within hours"
    else:
        impact = "Minimal population impact expected under current trajectory"

    return {
        "consensus": consensus,
        "action_plan": action_plan[:6],
        "overall_urgency": max_urgency,
        "confidence_score": round(avg_confidence, 2),
        "dissent_log": dissent_log if dissent_log else ["No significant dissent — agents aligned on assessment"],
        "affected_zones": affected_zones,
        "estimated_impact": impact
    }


async def run_parliament_session(pulse: CityPulse, trigger: str = "Scheduled analysis") -> ParliamentDecision:
    """
    MAIN ENTRY POINT: Run all 5 agents in parallel, collect their votes,
    and synthesize a consensus decision with full transparency.
    """
    t0 = time.time()
    session_id = f"parliament_{uuid.uuid4().hex[:12]}"
    logger.info(f"🏛️  Parliament session {session_id} starting — trigger: {trigger}")

    # Run all 5 agents CONCURRENTLY (this is the "never seen before" part)
    stances = await asyncio.gather(*[
        _run_single_agent(agent_name, pulse, trigger)
        for agent_name in _AGENTS.keys()
    ])

    synthesis = _synthesize_consensus(pulse, stances)
    causal_chain = _build_causal_chain(pulse, stances)

    decision = ParliamentDecision(
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
        trigger=trigger,
        city=pulse.city,
        stances=stances,
        consensus=synthesis["consensus"],
        action_plan=synthesis["action_plan"],
        overall_urgency=synthesis["overall_urgency"],
        confidence_score=synthesis["confidence_score"],
        dissent_log=synthesis["dissent_log"],
        causal_chain=causal_chain,
        affected_zones=synthesis["affected_zones"],
        estimated_impact=synthesis["estimated_impact"],
        processing_time_ms=round((time.time() - t0) * 1000, 1)
    )

    logger.info(f"🏛️  Parliament session {session_id} complete in "
                 f"{decision.processing_time_ms:.0f}ms — urgency: {decision.overall_urgency.value}")
    return decision
