"""
NARAD - Data schemas and models
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class AgentName(str, Enum):
    TRANSPORT   = "TransportAgent"
    HEALTH      = "HealthAgent"
    ENVIRONMENT = "EnvironmentAgent"
    ECONOMY     = "EconomyAgent"
    SAFETY      = "SafetyAgent"

class Severity(str, Enum):
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"
    CRITICAL = "critical"

class VoteDecision(str, Enum):
    APPROVE   = "approve"
    REJECT    = "reject"
    ABSTAIN   = "abstain"
    ESCALATE  = "escalate"


# ─── City Data ────────────────────────────────────────────────────────────────

class WeatherData(BaseModel):
    temperature: float
    humidity: float
    wind_speed: float
    wind_direction: str
    condition: str
    feels_like: float
    visibility: float
    pressure: float

class AQIData(BaseModel):
    aqi: int
    status: str          # Good / Moderate / Unhealthy / Very Unhealthy / Hazardous
    pm25: float
    pm10: float
    no2: float
    o3: float
    co: float
    so2: float
    color: str           # hex color for UI

class TrafficData(BaseModel):
    congestion_level: float   # 0-100
    avg_speed_kmh: float
    incidents: int
    affected_zones: List[str]
    travel_time_index: float  # 1.0 = free flow, 2.0 = double normal time
    hotspots: List[Dict[str, Any]]

class HospitalData(BaseModel):
    total_hospitals: int
    available_beds: int
    icu_available: int
    ambulances_active: int
    emergency_wait_minutes: float
    capacity_percent: float
    critical_facilities: List[str]
    manual_reports_count: int = 0       # how many hospitals are actively self-reporting
    manual_coverage_pct: float = 0.0    # what % of total_hospitals that represents


class ManualHospitalReport(BaseModel):
    """A hospital self-reporting its own live status — no external API needed."""
    hospital_name: str = Field(..., min_length=1, max_length=200)
    available_beds: int = Field(..., ge=0, le=10000)
    icu_available: int = Field(..., ge=0, le=2000)
    ambulances_active: int = Field(default=0, ge=0, le=500)
    emergency_wait_minutes: float = Field(default=15.0, ge=0, le=1440)
    reported_by: Optional[str] = Field(default=None, max_length=200)       # e.g. staff name/role, optional
    reported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SafetyData(BaseModel):
    active_incidents: int
    emergency_calls_1h: int
    police_response_minutes: float
    fire_units_deployed: int
    high_risk_zones: List[str]
    alert_level: str

class EconomyData(BaseModel):
    fuel_price_litre: float
    essential_goods_index: float
    market_activity: str
    utility_load_percent: float
    water_supply_status: str
    power_outages: int


# ─── City Pulse (combined live snapshot) ──────────────────────────────────────

class CityPulse(BaseModel):
    city: str
    timestamp: datetime
    weather: WeatherData
    aqi: AQIData
    traffic: TrafficData
    hospitals: HospitalData
    safety: SafetyData
    economy: EconomyData
    overall_health_score: float  # 0-100
    alerts: List[str]
    data_sources: Dict[str, str] = Field(default_factory=dict)  # domain -> "live" | "simulated"


# ─── Agent Parliament ──────────────────────────────────────────────────────────

class AgentStance(BaseModel):
    agent: AgentName
    emoji: str
    analysis: str
    recommendation: str
    confidence: float        # 0-1
    vote: VoteDecision
    urgency: Severity
    key_metrics: Dict[str, Any]
    dissent_reason: Optional[str] = None

class ParliamentDecision(BaseModel):
    session_id: str
    timestamp: datetime
    trigger: str                      # What triggered this session
    city: str
    stances: List[AgentStance]
    consensus: str                    # Final synthesized recommendation
    action_plan: List[str]            # Ordered action items
    overall_urgency: Severity
    confidence_score: float
    dissent_log: List[str]            # Where agents disagreed
    causal_chain: List[str]           # A→B→C causal reasoning
    affected_zones: List[str]
    estimated_impact: str
    processing_time_ms: float

class ParliamentSession(BaseModel):
    session_id: str
    status: Literal["running", "completed", "failed"]
    started_at: datetime
    decision: Optional[ParliamentDecision] = None
    error: Optional[str] = None


# ─── Scenario Simulation ──────────────────────────────────────────────────────

class ScenarioRequest(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = Field(..., max_length=500)
    parameters: Dict[str, Any]    # e.g. {"close_road": "NH-44", "duration_hours": 3}
    scenario_count: int = Field(default=500, le=2000)

class ScenarioOutcome(BaseModel):
    scenario_id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    outcomes: Dict[str, Any]
    traffic_impact: float
    health_impact: float
    economy_impact: float
    safety_impact: float
    environment_impact: float
    recommendation: str
    confidence: float
    processing_ms: float
    rapids_speedup: Optional[float] = None  # GPU vs CPU speedup ratio

class ScenarioComparison(BaseModel):
    scenarios: List[ScenarioOutcome]
    best_scenario: str
    worst_scenario: str
    rapids_benchmark: Optional[Dict[str, Any]] = None


# ─── Analysis Request ─────────────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    city: str = "Hyderabad"
    query: str
    priority_domains: Optional[List[str]] = None  # which agents to prioritize
    language: str = "english"  # english | hindi | telugu


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    language: str = "english"  # english | hindi | telugu


# ─── WebSocket Messages ───────────────────────────────────────────────────────

class WSEventType(str, Enum):
    CITY_PULSE      = "city_pulse"
    AGENT_SPEAKING  = "agent_speaking"
    PARLIAMENT_START= "parliament_start"
    PARLIAMENT_END  = "parliament_end"
    ALERT           = "alert"
    BENCHMARK       = "benchmark"
    DATA_UPDATE     = "data_update"
    ERROR           = "error"

class WSMessage(BaseModel):
    type: WSEventType
    payload: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Benchmark ────────────────────────────────────────────────────────────────

class RAPIDSBenchmark(BaseModel):
    operation: str
    dataset_size: int
    pandas_time_ms: float
    rapids_time_ms: Optional[float] = None
    speedup: Optional[float] = None
    using_gpu: bool
    notes: str
