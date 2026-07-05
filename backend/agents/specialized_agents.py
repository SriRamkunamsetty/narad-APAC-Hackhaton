"""
NARAD - The 5 Specialized ADK Intelligence Agents
Each agent is a domain expert that analyzes city data and produces recommendations.
They operate as members of the Agent Parliament.
"""
import asyncio
import logging
import httpx
from typing import Dict, Any
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from backend.config import GEMINI_MODEL

logger = logging.getLogger("narad.agents")


# ─── Tool Functions (real data + analysis) ───────────────────────────────────

def analyze_traffic_conditions(
    congestion_level: float,
    avg_speed_kmh: float,
    incidents: int,
    affected_zones: str,
    travel_time_index: float
) -> Dict[str, Any]:
    """
    Analyze current traffic conditions for a city and provide transport intelligence.
    Args:
        congestion_level: 0-100 scale (0=free flow, 100=gridlock)
        avg_speed_kmh: Average vehicle speed in km/h
        incidents: Number of active incidents
        affected_zones: Comma-separated list of congested zones
        travel_time_index: Multiplier vs free-flow time (1.0=normal, 2.0=double)
    Returns:
        Transport analysis with recommendations
    """
    severity = (
        "CRITICAL" if congestion_level > 80 else
        "HIGH" if congestion_level > 60 else
        "MODERATE" if congestion_level > 40 else "LOW"
    )

    recommendations = []
    if congestion_level > 70:
        recommendations.append("Activate smart signal timing optimization on major corridors")
        recommendations.append("Issue traffic diversion advisory via HMTV and Zomato/Swiggy fleet")
    if incidents > 5:
        recommendations.append(f"Deploy traffic police to {incidents} incident zones immediately")
    if travel_time_index > 2.0:
        recommendations.append("Recommend public transport (Metro, TSRTC) to reduce private vehicles")
    if avg_speed_kmh < 15:
        recommendations.append("Alert emergency vehicles for alternate routing through Outer Ring Road")

    return {
        "severity": severity,
        "congestion_level": congestion_level,
        "avg_speed_kmh": avg_speed_kmh,
        "incidents": incidents,
        "affected_zones": affected_zones,
        "estimated_delay_minutes": round((travel_time_index - 1) * 20, 1),
        "recommendations": recommendations,
        "emergency_vehicle_impact": "HIGH" if congestion_level > 75 else "MODERATE",
        "metro_ridership_recommendation": congestion_level > 65
    }


def analyze_health_capacity(
    available_beds: int,
    icu_available: int,
    capacity_percent: float,
    ambulances_active: int,
    emergency_wait_minutes: float,
    critical_facilities: str
) -> Dict[str, Any]:
    """
    Analyze healthcare system capacity and predict resource needs.
    Args:
        available_beds: Currently available hospital beds
        icu_available: Available ICU beds
        capacity_percent: Overall hospital system capacity usage (0-100)
        ambulances_active: Number of active ambulances
        emergency_wait_minutes: Average emergency room wait time
        critical_facilities: Comma-separated facilities under stress
    Returns:
        Healthcare analysis with surge predictions and resource recommendations
    """
    stress_level = (
        "CRITICAL" if capacity_percent > 90 else
        "HIGH" if capacity_percent > 80 else
        "MODERATE" if capacity_percent > 65 else "NORMAL"
    )

    # Predict next 6 hours
    predicted_surge = round(capacity_percent * 1.08, 1) if capacity_percent > 70 else capacity_percent

    recommendations = []
    if capacity_percent > 80:
        recommendations.append("Activate Hospital Surge Protocol — notify all medical staff on standby")
        recommendations.append("Prepare overflow facilities: convention centers, COVID-era field hospitals")
    if icu_available < 20:
        recommendations.append(f"ICU CRITICAL: Only {icu_available} ICU beds available — escalate to DGHS")
    if emergency_wait_minutes > 30:
        recommendations.append("Deploy additional emergency triage stations to reduce wait times")
    if ambulances_active > 25:
        recommendations.append("Request mutual aid ambulances from neighboring districts")

    return {
        "stress_level": stress_level,
        "capacity_percent": capacity_percent,
        "available_beds": available_beds,
        "icu_available": icu_available,
        "predicted_capacity_6h": predicted_surge,
        "emergency_wait_minutes": emergency_wait_minutes,
        "critical_facilities": critical_facilities,
        "recommendations": recommendations,
        "mass_casualty_readiness": "READY" if capacity_percent < 70 else "LIMITED",
        "patient_diversion_needed": capacity_percent > 85
    }


def analyze_environment(
    aqi: int,
    pm25: float,
    pm10: float,
    no2: float,
    temperature: float,
    humidity: float,
    wind_speed: float
) -> Dict[str, Any]:
    """
    Analyze environmental conditions and health risks for the city population.
    Args:
        aqi: Air Quality Index (0-500, higher = worse)
        pm25: PM2.5 particulate matter (μg/m³)
        pm10: PM10 particulate matter (μg/m³)
        no2: Nitrogen dioxide (μg/m³)
        temperature: Air temperature (°C)
        humidity: Relative humidity (%)
        wind_speed: Wind speed (km/h)
    Returns:
        Environmental risk assessment and public health recommendations
    """
    # Population at risk (Hyderabad ~10M)
    population = 10_000_000
    sensitive_pct = 0.15  # 15% vulnerable population
    at_risk = int(population * sensitive_pct) if aqi > 100 else 0
    all_at_risk = int(population * 0.4) if aqi > 150 else 0

    health_risk = (
        "HAZARDOUS" if aqi > 300 else
        "VERY HIGH" if aqi > 200 else
        "HIGH" if aqi > 150 else
        "MODERATE" if aqi > 100 else "LOW"
    )

    heat_stress = temperature > 38 and humidity > 70

    recommendations = []
    if aqi > 150:
        recommendations.append(f"Issue public health advisory for AQI {aqi} — distribute N95 masks")
        recommendations.append("Close outdoor schools, parks, and construction sites")
    if aqi > 200:
        recommendations.append("Implement odd-even vehicle scheme to reduce vehicular emissions")
        recommendations.append("Shut industrial units in pollution hotspots for 24 hours")
    if heat_stress:
        recommendations.append("Open cooling centers in all government buildings")
        recommendations.append("Increase ORS distribution in slum areas through ASHA workers")
    if wind_speed < 5:
        recommendations.append("Low wind conditions: air pollutants accumulating — heightened alert")

    dispersion_hours = max(2, int(20 / max(wind_speed, 1)))

    return {
        "health_risk": health_risk,
        "aqi": aqi,
        "pm25": pm25,
        "pm10": pm10,
        "no2": no2,
        "population_at_risk": at_risk,
        "all_population_advisory": all_at_risk > 0,
        "heat_stress_alert": heat_stress,
        "pollution_dispersion_hours": dispersion_hours,
        "recommendations": recommendations,
        "school_closure_recommended": aqi > 150,
        "outdoor_activity_advisory": aqi > 100
    }


def analyze_economy_resources(
    utility_load_percent: float,
    power_outages: int,
    fuel_price_litre: float,
    essential_goods_index: float,
    market_activity: str,
    water_supply_status: str
) -> Dict[str, Any]:
    """
    Analyze economic stress indicators and resource availability.
    Args:
        utility_load_percent: Electrical grid load (% of capacity)
        power_outages: Number of zones with active outages
        fuel_price_litre: Current petrol price per litre (₹)
        essential_goods_index: Essential goods price index (100 = baseline)
        market_activity: Current market status (Active/Closed)
        water_supply_status: Water supply system status
    Returns:
        Economic impact assessment and resource optimization recommendations
    """
    grid_stress = utility_load_percent > 85
    inflation_alert = essential_goods_index > 108

    recommendations = []
    if utility_load_percent > 85:
        recommendations.append("Activate demand-side management: request industries to reduce load by 15%")
        recommendations.append("Pre-position emergency DG sets at hospitals and water pumping stations")
    if power_outages > 2:
        recommendations.append(f"TRANSCO alert: {power_outages} zones on outage — fast-track restoration")
    if essential_goods_index > 108:
        recommendations.append("Notify civil supplies dept — essential goods index elevated")
        recommendations.append("Activate price monitoring in wholesale mandis")
    if water_supply_status != "Normal":
        recommendations.append("Reroute water tanker fleet to pressure-deficit zones")

    estimated_cost_crore = round(power_outages * 2.4 + (utility_load_percent - 80) * 0.8, 1)

    return {
        "grid_stress": grid_stress,
        "utility_load": utility_load_percent,
        "power_outages": power_outages,
        "fuel_price": fuel_price_litre,
        "essential_goods_index": essential_goods_index,
        "inflation_alert": inflation_alert,
        "water_supply": water_supply_status,
        "estimated_disruption_cost_crore": max(0, estimated_cost_crore),
        "recommendations": recommendations,
        "emergency_resource_alert": utility_load_percent > 90 or power_outages > 3
    }


def analyze_public_safety(
    active_incidents: int,
    emergency_calls_1h: int,
    police_response_minutes: float,
    fire_units_deployed: int,
    high_risk_zones: str,
    alert_level: str
) -> Dict[str, Any]:
    """
    Analyze public safety situation and emergency response capacity.
    Args:
        active_incidents: Number of currently active incidents
        emergency_calls_1h: Emergency calls received in last hour
        police_response_minutes: Average police response time
        fire_units_deployed: Active fire fighting units
        high_risk_zones: Comma-separated high-risk areas
        alert_level: Current alert level (Green/Yellow/Orange/Red)
    Returns:
        Safety assessment with emergency response recommendations
    """
    response_degraded = police_response_minutes > 12
    high_tempo = emergency_calls_1h > 40

    # Risk matrix
    risk_score = (
        active_incidents * 3 +
        (emergency_calls_1h - 20) * 0.5 +
        (police_response_minutes - 8) * 2 +
        fire_units_deployed * 2
    )

    severity = (
        "CRITICAL" if risk_score > 80 else
        "HIGH" if risk_score > 50 else
        "ELEVATED" if risk_score > 25 else "NORMAL"
    )

    recommendations = []
    if active_incidents > 10:
        recommendations.append("Activate District Emergency Operations Center (DEOC)")
        recommendations.append(f"Deploy rapid response teams to: {high_risk_zones}")
    if response_degraded:
        recommendations.append("Police response time exceeding SLA — request additional patrol units")
    if high_tempo:
        recommendations.append(f"High call volume ({emergency_calls_1h}/hr) — scale up 100/112 capacity")
    if fire_units_deployed > 8:
        recommendations.append("Fire department at high deployment — request mutual aid from GHMC")
    if alert_level in ["Orange", "Red"]:
        recommendations.append(f"ALERT LEVEL {alert_level}: Notify District Collector and Commissioner")

    return {
        "severity": severity,
        "risk_score": round(risk_score, 1),
        "active_incidents": active_incidents,
        "emergency_calls_1h": emergency_calls_1h,
        "police_response_minutes": police_response_minutes,
        "fire_units_deployed": fire_units_deployed,
        "high_risk_zones": high_risk_zones,
        "alert_level": alert_level,
        "response_capacity": "STRAINED" if response_degraded or high_tempo else "NORMAL",
        "recommendations": recommendations,
        "deoc_activation_recommended": active_incidents > 10 or alert_level == "Red"
    }


# ─── Build the 5 ADK Agents ──────────────────────────────────────────────────

def build_transport_agent() -> LlmAgent:
    return LlmAgent(
        name="TransportAgent",
        model=GEMINI_MODEL,
        description=(
            "Expert in urban mobility, traffic management, transportation systems, "
            "and road network optimization for Indian cities."
        ),
        instruction=(
            "You are the Transport Intelligence Agent of NARAD, Hyderabad's city AI parliament. "
            "Analyze traffic congestion, road incidents, public transport load, and mobility patterns. "
            "Your role is to assess transport stress and recommend interventions to maintain mobility. "
            "Always consider emergency vehicle access, public transport alternatives, and the economic "
            "cost of congestion. Reference specific Hyderabad roads, junctions, and transport systems. "
            "Be specific, quantitative, and action-oriented. Vote with confidence."
        ),
        tools=[FunctionTool(func=analyze_traffic_conditions)],
    )


def build_health_agent() -> LlmAgent:
    return LlmAgent(
        name="HealthAgent",
        model=GEMINI_MODEL,
        description=(
            "Expert in public health systems, hospital capacity management, "
            "emergency medical services, and epidemic surveillance."
        ),
        instruction=(
            "You are the Health Intelligence Agent of NARAD, Hyderabad's city AI parliament. "
            "Monitor hospital capacity, emergency medical services, disease surveillance, and "
            "public health emergencies. Your role is critical — human lives depend on your analysis. "
            "Always assess mass casualty preparedness, ICU availability, ambulance response times, "
            "and surge capacity. Reference NIMS, Osmania General, Gandhi Hospital, AIIMS Hyderabad. "
            "Consider vulnerable populations: elderly, children, pregnant women. "
            "Be proactive — predict surges before they happen. Vote decisively."
        ),
        tools=[FunctionTool(func=analyze_health_capacity)],
    )


def build_environment_agent() -> LlmAgent:
    return LlmAgent(
        name="EnvironmentAgent",
        model=GEMINI_MODEL,
        description=(
            "Expert in air quality monitoring, climate resilience, environmental health, "
            "pollution control, and sustainable urban planning."
        ),
        instruction=(
            "You are the Environment Intelligence Agent of NARAD, Hyderabad's city AI parliament. "
            "Monitor air quality (AQI, PM2.5, PM10), weather patterns, heat stress, flooding risks, "
            "and environmental health impacts. Your role is to protect 10 million Hyderabadis "
            "from environmental hazards. Consider the causal chain: pollution → hospital admissions → "
            "economic loss. Reference Hyderabad's seasonal patterns (monsoon, summer heat, winter smog). "
            "Advocate for preventive action — closing schools, restricting vehicles, opening cooling centers. "
            "Provide clear thresholds and timelines. Vote based on population health risk."
        ),
        tools=[FunctionTool(func=analyze_environment)],
    )


def build_economy_agent() -> LlmAgent:
    return LlmAgent(
        name="EconomyAgent",
        model=GEMINI_MODEL,
        description=(
            "Expert in urban economic systems, utility infrastructure, supply chains, "
            "resource allocation, and fiscal impact assessment."
        ),
        instruction=(
            "You are the Economy Intelligence Agent of NARAD, Hyderabad's city AI parliament. "
            "Monitor utility grid loads, fuel prices, essential goods availability, water supply, "
            "and economic disruption risks. Your role is to quantify the economic cost of city "
            "disruptions and optimize resource allocation. Reference Hyderabad's HMWSSB (water), "
            "TSSPDCL/TSNPDCL (electricity), and civil supplies department. "
            "Always provide cost estimates in ₹ crore. Weigh short-term disruption vs long-term impact. "
            "Vote pragmatically — balance fiscal responsibility with public welfare."
        ),
        tools=[FunctionTool(func=analyze_economy_resources)],
    )


def build_safety_agent() -> LlmAgent:
    return LlmAgent(
        name="SafetyAgent",
        model=GEMINI_MODEL,
        description=(
            "Expert in public safety, law enforcement, emergency response, "
            "disaster management, and crime pattern analysis."
        ),
        instruction=(
            "You are the Safety Intelligence Agent of NARAD, Hyderabad's city AI parliament. "
            "Monitor active incidents, emergency response times, law enforcement capacity, "
            "fire safety, and disaster readiness. Your role is to protect lives and maintain "
            "public order across Hyderabad. Reference Hyderabad Police, GHMC Disaster Management, "
            "SDRF (State Disaster Response Force), and the Integrated Command & Control Centre (ICCC). "
            "Be direct about threat levels. Recommend resource deployment with specific units and locations. "
            "Vote assertively — public safety cannot be compromised."
        ),
        tools=[FunctionTool(func=analyze_public_safety)],
    )
