"""
NARAD - Live Data Ingestion Engine
Pulls from real APIs: OpenWeatherMap, OpenAQ, News, and simulates traffic/health/safety
with realistic patterns based on time-of-day, Indian city context
"""
import asyncio
import httpx
import math
import random
from datetime import datetime, timezone
from typing import Optional
import logging

from backend.config import (
    OPENWEATHER_API_KEY, OPENAQ_API_KEY, NEWS_API_KEY, GOOGLE_MAPS_API_KEY,
    DEFAULT_CITY, DEFAULT_LAT, DEFAULT_LNG
)
from backend.models.schemas import (
    WeatherData, AQIData, TrafficData, HospitalData,
    SafetyData, EconomyData, CityPulse
)

logger = logging.getLogger("narad.feeds")


async def _fetch_with_retry(client: httpx.AsyncClient, url: str, params: dict = None,
                             headers: dict = None, max_attempts: int = 2) -> Optional[httpx.Response]:
    """
    Single retry with short backoff for transient network failures. Not
    infinite retries — a real outage should fall through to simulation
    quickly, not hang the request pipeline. Returns None (never raises) if
    all attempts fail, so callers keep their existing try/except-based
    simulation fallback unchanged.
    """
    last_error = None
    for attempt in range(max_attempts):
        try:
            return await client.get(url, params=params, headers=headers)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            last_error = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5 * (attempt + 1))  # 0.5s, then 1s
    logger.warning(f"All {max_attempts} attempts failed for {url}: {last_error}")
    return None


def _time_factor() -> float:
    """Returns a 0-1 factor based on hour of day (peaks at morning/evening rush)"""
    hour = datetime.now().hour
    # Rush hour peaks: 8-10 AM and 5-8 PM
    morning_peak = math.exp(-0.5 * ((hour - 9) / 1.5) ** 2)
    evening_peak = math.exp(-0.5 * ((hour - 18) / 1.5) ** 2)
    return min(1.0, morning_peak + evening_peak)


def _noise(base: float, pct: float = 0.08) -> float:
    """Add realistic noise to a metric"""
    return base * (1 + random.uniform(-pct, pct))


async def fetch_weather(city: str = DEFAULT_CITY) -> tuple[WeatherData, str]:
    """Fetch live weather from OpenWeatherMap API. Returns (data, 'live'|'simulated')."""
    if OPENWEATHER_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await _fetch_with_retry(
                    client, "https://api.openweathermap.org/data/2.5/weather",
                    params={"q": f"{city},IN", "appid": OPENWEATHER_API_KEY, "units": "metric"}
                )
                if r and r.status_code == 200:
                    d = r.json()
                    return WeatherData(
                        temperature=d["main"]["temp"],
                        humidity=d["main"]["humidity"],
                        wind_speed=d["wind"]["speed"],
                        wind_direction=_wind_dir(d["wind"].get("deg", 0)),
                        condition=d["weather"][0]["description"].title(),
                        feels_like=d["main"]["feels_like"],
                        visibility=d.get("visibility", 10000) / 1000,
                        pressure=d["main"]["pressure"]
                    ), "live"
        except Exception as e:
            logger.warning(f"Weather API failed: {e}, using simulation")

    # Realistic Hyderabad weather simulation
    month = datetime.now().month
    hour  = datetime.now().hour
    base_temp = {6: 28, 7: 27, 8: 27, 9: 28, 10: 27, 11: 24,
                 12: 21, 1: 19, 2: 22, 3: 27, 4: 32, 5: 35}.get(month, 28)
    temp_variation = -3 if hour < 6 else (2 if hour < 12 else 4 if hour < 16 else 1)

    conditions = ["Clear Sky", "Partly Cloudy", "Overcast", "Light Rain", "Hazy"]
    weights    = [0.45, 0.25, 0.15, 0.10, 0.05]
    condition  = random.choices(conditions, weights=weights)[0]

    return WeatherData(
        temperature=_noise(base_temp + temp_variation),
        humidity=_noise(65 if month in [7, 8, 9] else 45),
        wind_speed=_noise(12),
        wind_direction=random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
        condition=condition,
        feels_like=_noise(base_temp + temp_variation + 2),
        visibility=_noise(8.5),
        pressure=_noise(1013)
    ), "simulated"


async def fetch_aqi(city: str = DEFAULT_CITY) -> tuple[AQIData, str]:
    """Fetch live AQI from OpenAQ API. Returns (data, 'live'|'simulated')."""
    if OPENAQ_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await _fetch_with_retry(
                    client, "https://api.openaq.org/v3/locations",
                    params={"city": city, "country": "IN", "limit": 5},
                    headers={"X-API-Key": OPENAQ_API_KEY}
                )
                if r and r.status_code == 200:
                    data = r.json()
                    if data.get("results"):
                        # Use first available location's latest readings
                        loc = data["results"][0]
                        sensors = {s["parameter"]["name"]: s["latest"]["value"]
                                   for s in loc.get("sensors", [])
                                   if s.get("latest")}
                        pm25 = sensors.get("pm25", 55.0)
                        pm10 = sensors.get("pm10", 90.0)
                        aqi  = _pm25_to_aqi(pm25)
                        return AQIData(
                            aqi=aqi, status=_aqi_status(aqi), pm25=pm25, pm10=pm10,
                            no2=sensors.get("no2", 35.0), o3=sensors.get("o3", 40.0),
                            co=sensors.get("co", 0.8), so2=sensors.get("so2", 10.0),
                            color=_aqi_color(aqi)
                        ), "live"
        except Exception as e:
            logger.warning(f"OpenAQ failed: {e}, using simulation")

    # Simulate realistic Hyderabad AQI (seasonally adjusted)
    month = datetime.now().month
    hour  = datetime.now().hour
    base_pm25 = {11: 85, 12: 95, 1: 90, 2: 70, 3: 55, 4: 50,
                  5: 48, 6: 45, 7: 42, 8: 40, 9: 45, 10: 65}.get(month, 60)
    # Traffic rush → higher pollution
    peak = _time_factor()
    pm25 = _noise(base_pm25 * (1 + 0.3 * peak))
    pm10 = pm25 * 1.6
    aqi  = _pm25_to_aqi(pm25)

    return AQIData(
        aqi=aqi, status=_aqi_status(aqi),
        pm25=round(pm25, 1), pm10=round(pm10, 1),
        no2=_noise(35 * (1 + 0.2 * peak)),
        o3=_noise(42), co=_noise(0.85), so2=_noise(12),
        color=_aqi_color(aqi)
    ), "simulated"


async def fetch_traffic(city: str = DEFAULT_CITY) -> tuple[TrafficData, str]:
    """
    Fetch REAL live traffic using Google Maps Distance Matrix API.
    Measures actual current congestion across major Hyderabad corridors by
    comparing live duration_in_traffic against free-flow duration.
    Falls back to realistic simulation if no API key or the call fails.
    Returns (data, 'live'|'simulated').
    """
    if GOOGLE_MAPS_API_KEY:
        try:
            return await _fetch_traffic_google_maps(), "live"
        except Exception as e:
            logger.warning(f"Google Maps traffic fetch failed: {e}, using simulation")

    return _simulate_traffic(), "simulated"


# Major Hyderabad corridors used as live congestion probes.
# Each is a real origin→destination pair on a well-known route.
_HYD_CORRIDORS = [
    {"zone": "Gachibowli–Hitech City",  "origin": "Gachibowli, Hyderabad",       "destination": "Hitech City, Hyderabad"},
    {"zone": "Kukatpally–Secunderabad", "origin": "Kukatpally, Hyderabad",       "destination": "Secunderabad, Hyderabad"},
    {"zone": "Banjara Hills–Madhapur",  "origin": "Banjara Hills, Hyderabad",    "destination": "Madhapur, Hyderabad"},
    {"zone": "LB Nagar–Abids",          "origin": "LB Nagar, Hyderabad",         "destination": "Abids, Hyderabad"},
]


async def _fetch_traffic_google_maps() -> TrafficData:
    """Query Distance Matrix API with departure_time=now for live traffic ratios"""
    async with httpx.AsyncClient(timeout=8.0) as client:
        results = []
        for corridor in _HYD_CORRIDORS:
            r = await client.get(
                "https://maps.googleapis.com/maps/api/distancematrix/json",
                params={
                    "origins": corridor["origin"],
                    "destinations": corridor["destination"],
                    "departure_time": "now",
                    "traffic_model": "best_guess",
                    "mode": "driving",
                    "key": GOOGLE_MAPS_API_KEY,
                }
            )
            data = r.json()
            if data.get("status") != "OK":
                continue
            element = data["rows"][0]["elements"][0]
            if element.get("status") != "OK":
                continue

            free_flow_s = element["duration"]["value"]
            live_s      = element.get("duration_in_traffic", element["duration"])["value"]
            distance_km = element["distance"]["value"] / 1000
            ratio       = live_s / free_flow_s if free_flow_s > 0 else 1.0

            results.append({
                "zone": corridor["zone"],
                "ratio": ratio,
                "avg_speed_kmh": (distance_km / (live_s / 3600)) if live_s > 0 else 0,
            })

        if not results:
            raise ValueError("No valid Distance Matrix results returned")

        avg_ratio = sum(r["ratio"] for r in results) / len(results)
        avg_speed = sum(r["avg_speed_kmh"] for r in results) / len(results)
        congestion_level = min(100, max(0, (avg_ratio - 1.0) * 100))
        affected = [r["zone"] for r in results if r["ratio"] > 1.3]

        return TrafficData(
            congestion_level=round(congestion_level, 1),
            avg_speed_kmh=round(avg_speed, 1),
            incidents=len(affected),
            affected_zones=affected,
            travel_time_index=round(avg_ratio, 2),
            hotspots=[
                {"zone": r["zone"], "severity": round(min(1.0, (r["ratio"] - 1) ), 2),
                 "lat": DEFAULT_LAT, "lng": DEFAULT_LNG}
                for r in results if r["ratio"] > 1.15
            ]
        )


def _simulate_traffic() -> TrafficData:
    """Realistic Hyderabad traffic simulation (used when no Google Maps key is set)"""
    peak = _time_factor()
    congestion = min(95, _noise(20 + 70 * peak))
    avg_speed  = max(8, _noise(55 - 40 * (congestion / 100)))
    incidents  = int(_noise(2 + 5 * peak))

    hyderabad_zones = [
        "Hitech City", "Banjara Hills", "Jubilee Hills", "Secunderabad",
        "Kukatpally", "Gachibowli", "Kondapur", "Madhapur", "LB Nagar"
    ]
    n_affected = max(1, int(congestion / 15))
    affected   = random.sample(hyderabad_zones, min(n_affected, len(hyderabad_zones)))

    hotspots = [
        {"zone": z, "severity": round(_noise(congestion / 100), 2),
         "lat": DEFAULT_LAT + random.uniform(-0.1, 0.1),
         "lng": DEFAULT_LNG + random.uniform(-0.1, 0.1)}
        for z in affected[:4]
    ]

    return TrafficData(
        congestion_level=round(congestion, 1),
        avg_speed_kmh=round(avg_speed, 1),
        incidents=incidents,
        affected_zones=affected,
        travel_time_index=round(1 + (congestion / 100) * 2.5, 2),
        hotspots=hotspots
    )


async def fetch_hospitals(city: str = DEFAULT_CITY) -> tuple[HospitalData, str]:
    """
    Hospital capacity — prioritizes REAL manual self-reports from hospital staff
    (no public HMIS API exists for a hackathon team to integrate against), and
    fills any remaining unreported hospitals with realistic simulation so the
    city-wide aggregate stays meaningful.
    Returns (data, 'manual'|'simulated').
    """
    from backend.data.manual_reports import get_fresh_hospital_reports
    reports = get_fresh_hospital_reports()

    total_hospitals = 47
    total_bed_capacity = 4200
    total_icu_capacity = 320

    if reports:
        # Real numbers from hospitals that are actively self-reporting
        reported_beds   = sum(r.available_beds for r in reports)
        reported_icu    = sum(r.icu_available for r in reports)
        reported_ambul  = sum(r.ambulances_active for r in reports)
        reported_wait   = sum(r.emergency_wait_minutes for r in reports) / len(reports)
        reported_count  = len(reports)
        coverage_pct    = min(100.0, (reported_count / total_hospitals) * 100)

        # Simulate the remainder of hospitals that haven't self-reported yet,
        # so the city-wide total isn't misleadingly small.
        remaining_hospitals = max(0, total_hospitals - reported_count)
        remaining_bed_capacity = max(0, total_bed_capacity - reported_count * (total_bed_capacity // total_hospitals))
        remaining_icu_capacity = max(0, total_icu_capacity - reported_count * (total_icu_capacity // total_hospitals))

        peak = _time_factor()
        sim_capacity_pct = _noise(52 + 30 * peak)
        sim_available_beds = int(remaining_bed_capacity * (1 - sim_capacity_pct / 100)) if remaining_hospitals else 0
        sim_icu_available  = int(remaining_icu_capacity * (1 - (sim_capacity_pct + 8) / 100)) if remaining_hospitals else 0

        available_beds = reported_beds + max(0, sim_available_beds)
        icu_available  = reported_icu + max(0, sim_icu_available)
        capacity_percent = round(100 * (1 - available_beds / total_bed_capacity), 1)

        critical = [r.hospital_name for r in reports if r.icu_available <= 2]

        return HospitalData(
            total_hospitals=total_hospitals,
            available_beds=max(0, available_beds),
            icu_available=max(0, icu_available),
            ambulances_active=reported_ambul + int(_noise(10 + 8 * peak)),
            emergency_wait_minutes=round(reported_wait, 1),
            capacity_percent=min(98, max(0, capacity_percent)),
            critical_facilities=critical,
            manual_reports_count=reported_count,
            manual_coverage_pct=round(coverage_pct, 1)
        ), "manual"

    # No fresh manual reports at all — full simulation (would be replaced by
    # a real HMIS API integration the moment one becomes publicly available)
    peak = _time_factor()
    capacity_pct = _noise(52 + 30 * peak)

    critical = []
    if capacity_pct > 85:
        critical = random.sample([
            "NIMS", "Osmania General", "Gandhi Hospital", "KIMS"
        ], k=random.randint(1, 2))

    available  = int(total_bed_capacity * (1 - capacity_pct / 100))
    icu_pct    = capacity_pct + random.uniform(5, 15)  # ICU fills faster

    return HospitalData(
        total_hospitals=total_hospitals,
        available_beds=max(50, available),
        icu_available=max(5, int(total_icu_capacity * (1 - icu_pct / 100))),
        ambulances_active=int(_noise(18 + 12 * peak)),
        emergency_wait_minutes=_noise(12 + 25 * peak),
        capacity_percent=round(min(98, capacity_pct), 1),
        critical_facilities=critical,
        manual_reports_count=0,
        manual_coverage_pct=0.0
    ), "simulated"


async def fetch_safety(city: str = DEFAULT_CITY) -> SafetyData:
    """Simulate safety & emergency services data"""
    peak = _time_factor()
    hour = datetime.now().hour
    night_factor = 1.4 if (hour < 5 or hour > 22) else 1.0

    active_incidents = int(_noise((3 + 8 * peak) * night_factor))
    high_risk = []
    if active_incidents > 7:
        zones = ["Old City", "Secunderabad Station", "Charminar", "Afzalgunj", "Malakpet"]
        high_risk = random.sample(zones, k=min(active_incidents // 3, len(zones)))

    return SafetyData(
        active_incidents=active_incidents,
        emergency_calls_1h=int(_noise((15 + 40 * peak) * night_factor)),
        police_response_minutes=_noise(8 + 5 * peak),
        fire_units_deployed=int(_noise(3 + 4 * peak)),
        high_risk_zones=high_risk,
        alert_level=_incident_alert(active_incidents)
    )


async def fetch_economy(city: str = DEFAULT_CITY) -> EconomyData:
    """Simulate economic indicators for the city"""
    hour = datetime.now().hour
    is_market_hours = 9 <= hour <= 17

    utility_load = _noise(45 + 35 * _time_factor())
    power_outages = 0 if utility_load < 85 else random.randint(1, 4)

    return EconomyData(
        fuel_price_litre=_noise(96.72),
        essential_goods_index=_noise(100.4),
        market_activity="Active" if is_market_hours else "Closed",
        utility_load_percent=round(min(99, utility_load), 1),
        water_supply_status=random.choice(["Normal", "Normal", "Normal", "Pressure Low"]),
        power_outages=power_outages
    )


async def fetch_city_pulse(city: str = DEFAULT_CITY) -> CityPulse:
    """Fetch all city data in parallel and compute overall health score"""
    (weather, weather_src), (aqi, aqi_src), (traffic, traffic_src), \
        (hospitals, hospitals_src), safety, economy = await asyncio.gather(
        fetch_weather(city),
        fetch_aqi(city),
        fetch_traffic(city),
        fetch_hospitals(city),
        fetch_safety(city),
        fetch_economy(city)
    )

    data_sources = {
        "weather": weather_src,
        "aqi": aqi_src,
        "traffic": traffic_src,
        "hospitals": hospitals_src,       # "manual" once hospitals self-report, else "simulated"
        "safety": "simulated",     # no public real-time police/incident API exists
        "economy": "simulated",    # no reliable free real-time API for utility load/fuel price
    }

    # Compute overall city health score (0-100, higher = better)
    aqi_score      = max(0, 100 - aqi.aqi / 5)
    traffic_score  = max(0, 100 - traffic.congestion_level)
    health_score   = max(0, 100 - hospitals.capacity_percent)
    safety_score   = max(0, 100 - safety.active_incidents * 8)
    economy_score  = max(0, 100 - economy.utility_load_percent * 0.5)

    overall = round((aqi_score * 0.2 + traffic_score * 0.25 + health_score * 0.25
                     + safety_score * 0.2 + economy_score * 0.1), 1)

    # Generate contextual alerts
    alerts: list[str] = []
    if aqi.aqi > 150:
        alerts.append(f"🚨 AQI {aqi.aqi}: {aqi.status} – outdoor activity advisory issued")
    if traffic.congestion_level > 75:
        alerts.append(f"🚦 Severe congestion in {', '.join(traffic.affected_zones[:2])}")
    if hospitals.capacity_percent > 85:
        alerts.append(f"🏥 Hospital system at {hospitals.capacity_percent:.0f}% capacity")
    if safety.active_incidents > 8:
        alerts.append(f"🚔 Elevated incident activity: {safety.active_incidents} active cases")
    if economy.power_outages > 0:
        alerts.append(f"⚡ Power disruptions reported in {economy.power_outages} zones")

    return CityPulse(
        city=city,
        timestamp=datetime.now(timezone.utc),
        weather=weather, aqi=aqi, traffic=traffic,
        hospitals=hospitals, safety=safety, economy=economy,
        overall_health_score=overall,
        alerts=alerts,
        data_sources=data_sources
    )


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _pm25_to_aqi(pm25: float) -> int:
    """Convert PM2.5 to AQI using US EPA formula"""
    breakpoints = [
        (0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500)
    ]
    for lo, hi, aqi_lo, aqi_hi in breakpoints:
        if lo <= pm25 <= hi:
            return int(((aqi_hi - aqi_lo) / (hi - lo)) * (pm25 - lo) + aqi_lo)
    return 500

def _aqi_status(aqi: int) -> str:
    if aqi <= 50:   return "Good"
    if aqi <= 100:  return "Moderate"
    if aqi <= 150:  return "Unhealthy for Sensitive"
    if aqi <= 200:  return "Unhealthy"
    if aqi <= 300:  return "Very Unhealthy"
    return "Hazardous"

def _aqi_color(aqi: int) -> str:
    if aqi <= 50:   return "#00E400"
    if aqi <= 100:  return "#FFFF00"
    if aqi <= 150:  return "#FF7E00"
    if aqi <= 200:  return "#FF0000"
    if aqi <= 300:  return "#8F3F97"
    return "#7E0023"

def _wind_dir(deg: float) -> str:
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[int((deg + 22.5) / 45) % 8]

def _incident_alert(incidents: int) -> str:
    if incidents <= 3:  return "Green"
    if incidents <= 7:  return "Yellow"
    if incidents <= 12: return "Orange"
    return "Red"
