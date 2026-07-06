"""
NARAD - "Ask NARAD" Natural Language Concierge

Directly satisfies PS1's core requirement: "answer questions in natural
language." This is a lightweight RAG interface — it grounds every answer in
real, current context (live city pulse + latest parliament decision +, when
BigQuery is connected, similar past incidents) rather than letting Gemini
free-associate. It also supports Telugu and Hindi, addressing PS1's
"Accessibility and inclusive communities" solution area directly — most
Hyderabad residents are more comfortable in Telugu than English for a civic
tool like this.

This intentionally does NOT re-run the 5-agent parliament — it's meant to be
a fast, conversational layer on top of whatever the parliament already
decided, for a human (a city official, a journalist, a citizen) who just
wants a plain-language answer right now.
"""
import logging
from typing import Dict, Any, Optional, List

from backend.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.models.schemas import CityPulse, ParliamentDecision
from backend.data import bigquery_store

logger = logging.getLogger("narad.concierge")

_LANGUAGE_NAMES = {
    "english": "English",
    "hindi": "Hindi (हिन्दी)",
    "telugu": "Telugu (తెలుగు)",
}


def _build_context(pulse: Optional[CityPulse], decision: Optional[ParliamentDecision]) -> tuple[str, List[str]]:
    """Assemble grounding context from live state + BigQuery history. Returns (context_text, sources_used)."""
    sources_used = []
    parts = []

    if pulse:
        parts.append(f"""CURRENT CITY STATE — {pulse.city}, {pulse.timestamp.strftime('%Y-%m-%d %H:%M UTC')}:
- Weather: {pulse.weather.temperature:.1f}°C, {pulse.weather.condition}
- Air Quality: AQI {pulse.aqi.aqi} ({pulse.aqi.status})
- Traffic: {pulse.traffic.congestion_level:.0f}% congestion, affected zones: {', '.join(pulse.traffic.affected_zones) or 'none'}
- Hospitals: {pulse.hospitals.capacity_percent:.0f}% capacity, {pulse.hospitals.available_beds} beds free
  ({pulse.hospitals.manual_reports_count} hospitals self-reporting live data)
- Safety: {pulse.safety.active_incidents} active incidents, alert level {pulse.safety.alert_level}
- Overall city health score: {pulse.overall_health_score:.0f}/100
- Active alerts: {'; '.join(pulse.alerts) if pulse.alerts else 'none'}""")
        sources_used.append("live_city_pulse")

    if decision:
        parts.append(f"""LATEST AGENT PARLIAMENT DECISION (session {decision.session_id}):
- Trigger: {decision.trigger}
- Consensus: {decision.consensus}
- Overall urgency: {decision.overall_urgency.value}
- Causal chain: {' → '.join(decision.causal_chain) if decision.causal_chain else 'none identified'}
- Dissent: {'; '.join(decision.dissent_log)}
- Action plan: {'; '.join(decision.action_plan) if decision.action_plan else 'none'}""")
        sources_used.append("latest_parliament_decision")

    if decision and bigquery_store.BIGQUERY_AVAILABLE:
        similar = bigquery_store.query_similar_past_decisions(
            overall_urgency=decision.overall_urgency.value, city=decision.city, limit=3
        )
        if similar:
            past = "\n".join(
                f"- {s['timestamp']}: {s['trigger']} → {s['consensus']}" for s in similar
            )
            parts.append(f"SIMILAR PAST INCIDENTS (from BigQuery history):\n{past}")
            sources_used.append("bigquery_historical_decisions")

    return "\n\n".join(parts) if parts else "No live city data available yet.", sources_used


async def ask_narad(question: str, language: str = "english",
                     pulse: Optional[CityPulse] = None,
                     decision: Optional[ParliamentDecision] = None) -> Dict[str, Any]:
    """
    Answer a free-form natural-language question about the city, grounded in
    real current data. Returns {answer, sources_used, language, error?}.
    """
    context, sources_used = _build_context(pulse, decision)
    lang_name = _LANGUAGE_NAMES.get(language, "English")

    if not GEMINI_API_KEY:
        return {
            "answer": ("I can't reach Gemini right now because no GEMINI_API_KEY is configured. "
                       "Get a free key at https://aistudio.google.com/app/apikey and add it to .env."),
            "sources_used": [],
            "language": language,
            "error": "GEMINI_API_KEY not configured",
        }

    prompt = f"""You are NARAD, an AI city intelligence assistant for Hyderabad. You answer questions
from city officials, journalists, and residents about current city conditions, grounded ONLY in
the real data below — never invent specifics (numbers, locations, times) that aren't in this context.
If the context doesn't contain what's needed to answer, say so honestly rather than guessing.

{context}

Respond in {lang_name}. Be direct, specific, and cite the actual numbers from the context above.
Keep your answer to 2-4 sentences unless the question genuinely requires more detail.

QUESTION: {question}"""

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return {
            "answer": response.text,
            "sources_used": sources_used,
            "language": language,
        }
    except Exception as e:
        logger.error(f"Ask NARAD failed: {e}")
        return {
            "answer": "I hit an error trying to answer that — please try again in a moment.",
            "sources_used": sources_used,
            "language": language,
            "error": f"{type(e).__name__}: {e}",
        }
