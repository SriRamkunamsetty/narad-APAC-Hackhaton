"""
NARAD - Main FastAPI Application
Real-time city intelligence API with WebSocket streaming, REST endpoints,
and background parliament sessions.
"""
import asyncio
import logging
import json
import os
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import (
    APP_NAME, APP_VERSION, DEFAULT_CITY, PARLIAMENT_INTERVAL, DATA_REFRESH_INTERVAL,
    ALLOWED_ORIGINS
)
from backend.data.live_feeds import fetch_city_pulse
from backend.data.rapids_engine import (
    run_benchmark, evaluate_scenario, detect_anomalies, GPU_AVAILABLE
)
from backend.agents.parliament import run_parliament_session
from backend.agents.concierge import ask_narad
from backend.data import bigquery_store
from backend.security import verify_api_key, rate_limiter, audit_log_action
from backend.models.schemas import (
    ScenarioRequest, WSMessage, WSEventType, CityPulse, ParliamentDecision, ManualHospitalReport, AskRequest
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("narad.main")

# ─── Global State ──────────────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.current_pulse: CityPulse | None = None
        self.latest_decision: ParliamentDecision | None = None
        self.pulse_history: List[Dict] = []
        self.decision_history: List[ParliamentDecision] = []
        self.connected_clients: Set[WebSocket] = set()
        self.session_count = 0

state = AppState()


# ─── Background Tasks ──────────────────────────────────────────────────────────

async def broadcast(message: WSMessage):
    """Send a message to all connected WebSocket clients"""
    if not state.connected_clients:
        return
    dead = set()
    payload = message.model_dump_json()
    for client in state.connected_clients:
        try:
            await client.send_text(payload)
        except Exception:
            dead.add(client)
    state.connected_clients -= dead


async def data_refresh_loop():
    """Continuously fetch live city data and broadcast updates"""
    while True:
        try:
            pulse = await fetch_city_pulse(DEFAULT_CITY)
            state.current_pulse = pulse
            state.pulse_history.append({
                "timestamp": pulse.timestamp.isoformat(),
                "aqi": pulse.aqi.aqi,
                "congestion": pulse.traffic.congestion_level,
                "hospital_load": pulse.hospitals.capacity_percent,
                "incidents": pulse.safety.active_incidents,
            })
            state.pulse_history = state.pulse_history[-200:]  # in-memory buffer (fast, always available)

            # Persist to BigQuery for real historical analysis (no-op if unavailable)
            bigquery_store.insert_pulse_snapshot(pulse)

            await broadcast(WSMessage(type=WSEventType.CITY_PULSE, payload=pulse.model_dump(mode="json")))

            # Anomaly detection
            anomalies = detect_anomalies(state.pulse_history)
            for a in anomalies:
                await broadcast(WSMessage(type=WSEventType.ALERT, payload={"message": a, "source": "anomaly_detection"}))

            # Trigger parliament session if there are critical alerts
            if pulse.alerts and any("🚨" in a or "🏥" in a for a in pulse.alerts):
                asyncio.create_task(trigger_parliament("Auto-triggered: critical threshold breach detected"))

        except Exception as e:
            logger.error(f"Data refresh error: {e}")

        await asyncio.sleep(DATA_REFRESH_INTERVAL)


async def parliament_loop():
    """Periodically run scheduled parliament sessions"""
    await asyncio.sleep(10)  # let first data load happen
    while True:
        await trigger_parliament("Scheduled periodic analysis")
        await asyncio.sleep(PARLIAMENT_INTERVAL)


async def trigger_parliament(trigger: str):
    """Run a parliament session and broadcast results"""
    if state.current_pulse is None:
        return
    try:
        state.session_count += 1
        await broadcast(WSMessage(type=WSEventType.PARLIAMENT_START, payload={"trigger": trigger}))

        decision = await run_parliament_session(state.current_pulse, trigger)
        state.latest_decision = decision
        state.decision_history.append(decision)
        state.decision_history = state.decision_history[-20:]  # in-memory buffer

        # Persist to BigQuery for real historical analysis (no-op if unavailable)
        bigquery_store.insert_parliament_decision(decision)

        await broadcast(WSMessage(type=WSEventType.PARLIAMENT_END, payload=decision.model_dump(mode="json")))
    except Exception as e:
        logger.error(f"Parliament session error: {e}")
        await broadcast(WSMessage(type=WSEventType.ERROR, payload={"message": str(e)}))


_data_refresh_task = None
_parliament_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _data_refresh_task, _parliament_task
    logger.info(f"🚀 {APP_NAME} v{APP_VERSION} starting — GPU: {'✅ ACTIVE' if GPU_AVAILABLE else '⚠️ CPU fallback'}")

    # Attempt BigQuery connection — falls back to in-memory storage if unavailable
    bigquery_store.init_bigquery()

    # Warm up: fetch initial data
    try:
        state.current_pulse = await fetch_city_pulse(DEFAULT_CITY)
    except Exception as e:
        logger.error(f"Initial data fetch failed: {e}")

    _data_refresh_task = asyncio.create_task(data_refresh_loop())
    _parliament_task = asyncio.create_task(parliament_loop())
    yield
    _data_refresh_task.cancel()
    _parliament_task.cancel()
    logger.info("👋 NARAD shutting down")


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Basic security headers on every response. Defense-in-depth, not a
    substitute for a real security review."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Cloud Run terminates TLS in front of the app, so this is safe to send
    # unconditionally — the browser only sees requests over HTTPS anyway.
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    Attaches a short correlation ID to every request and to the logger
    context, so one request's flow through 5 concurrent agent calls (or any
    other multi-step operation) can be traced in Cloud Logging instead of
    being an unlabeled interleaved mess.
    """
    request_id = uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ─── REST Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/info")
async def api_info():
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": "operational",
        "gpu_acceleration": GPU_AVAILABLE,
        "description": "Neural Agentic Real-time Advisor for Decisions — AI city parliament for Hyderabad"
    }


@app.get("/")
async def root():
    """Serve the dashboard if built frontend exists, otherwise show API info"""
    index_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "index.html"
    )
    if os.path.isfile(index_path) and os.getenv("SERVE_STATIC", "false").lower() == "true":
        return FileResponse(index_path)
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": "operational",
        "gpu_acceleration": GPU_AVAILABLE,
        "description": "Neural Agentic Real-time Advisor for Decisions — AI city parliament for Hyderabad",
        "note": "Frontend not built. Run `npm run build` in /frontend or visit :5173 in dev mode."
    }


@app.get("/api/health")
async def health():
    """
    Deeper than a static ping — reports whether core dependencies are
    actually configured/reachable, and whether the background loops are
    still alive. A load balancer or uptime monitor should treat
    "degraded" as still-serving-traffic (fallbacks are working) but worth
    alerting on; only "unhealthy" should trigger an actual failover.
    """
    from backend.config import GEMINI_API_KEY, NARAD_ADMIN_API_KEY

    checks = {
        "gemini_configured": bool(GEMINI_API_KEY),
        "admin_key_configured": bool(NARAD_ADMIN_API_KEY),
        "bigquery_available": bigquery_store.BIGQUERY_AVAILABLE,
        "gpu_active": GPU_AVAILABLE,
        "city_pulse_loaded": state.current_pulse is not None,
        "background_loops_alive": (
            not _data_refresh_task.done() and not _parliament_task.done()
            if _data_refresh_task and _parliament_task else False
        ),
    }

    # "unhealthy" only for conditions that actually break core functionality —
    # missing optional integrations (BigQuery, GPU) degrade gracefully by design.
    is_unhealthy = not checks["city_pulse_loaded"] or not checks["background_loops_alive"]
    is_degraded = not checks["gemini_configured"] or not checks["admin_key_configured"]

    status = "unhealthy" if is_unhealthy else ("degraded" if is_degraded else "healthy")

    return {
        "status": status,
        "checks": checks,
        "sessions_run": state.session_count,
        "connected_clients": len(state.connected_clients),
        "data_points": len(state.pulse_history),
    }


@app.get("/api/city-pulse")
async def get_city_pulse():
    if state.current_pulse is None:
        raise HTTPException(503, "City data not yet available, please retry shortly")
    return state.current_pulse.model_dump(mode="json")


@app.get("/api/city-pulse/history")
async def get_pulse_history(hours: int = 24):
    """
    Historical city pulse data. Queries BigQuery for real persistent history
    when available; falls back to the in-memory rolling buffer (last ~200
    points, reset on restart) otherwise.
    """
    if bigquery_store.BIGQUERY_AVAILABLE:
        bq_history = bigquery_store.query_pulse_history(hours=hours, city=DEFAULT_CITY)
        if bq_history:
            return {
                "history": [
                    {
                        "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else row["timestamp"],
                        "aqi": row["aqi"],
                        "congestion": row["congestion"],
                        "hospital_load": row["hospital_load"],
                        "incidents": row["incidents"],
                    }
                    for row in bq_history
                ],
                "source": "bigquery",
            }
    return {"history": state.pulse_history, "source": "in_memory_buffer"}


@app.get("/api/parliament/latest")
async def get_latest_decision():
    if state.latest_decision is None:
        raise HTTPException(503, "No parliament session has run yet, please retry shortly")
    return state.latest_decision.model_dump(mode="json")


@app.get("/api/parliament/history")
async def get_decision_history(limit: int = 20):
    """
    Historical parliament decisions. Queries BigQuery for real persistent
    history when available; falls back to the in-memory buffer (last 20,
    reset on restart) otherwise.
    """
    if bigquery_store.BIGQUERY_AVAILABLE:
        bq_decisions = bigquery_store.query_recent_decisions(limit=limit, city=DEFAULT_CITY)
        if bq_decisions:
            return {
                "decisions": [json.loads(row["raw_json"]) for row in bq_decisions if row.get("raw_json")],
                "source": "bigquery",
            }
    return {
        "decisions": [d.model_dump(mode="json") for d in state.decision_history],
        "source": "in_memory_buffer",
    }


@app.post("/api/parliament/trigger")
async def manual_trigger(
    reason: str = "Manual trigger by user",
    request: Request = None,
    api_key: str = Depends(verify_api_key),
):
    """
    Manually trigger a parliament session. Requires an API key — each session
    costs 5 Gemini calls, so this is gated to prevent abuse/cost drain.
    """
    client_ip = request.client.host if request and request.client else "unknown"
    audit_log_action("parliament_trigger", identity=f"api_key:{api_key[:6]}...", details={"reason": reason}, client_ip=client_ip)
    asyncio.create_task(trigger_parliament(reason))
    return {"status": "triggered", "reason": reason}


@app.post("/api/scenario/simulate", dependencies=[Depends(rate_limiter(max_requests=20, window_seconds=60))])
async def simulate_scenario(request: ScenarioRequest):
    """Run a what-if scenario simulation using NVIDIA RAPIDS. Rate-limited (compute cost)."""
    if state.current_pulse is None:
        raise HTTPException(503, "City data not available")

    city_state = {
        "congestion": state.current_pulse.traffic.congestion_level,
        "hospital_load": state.current_pulse.hospitals.capacity_percent,
        "aqi": state.current_pulse.aqi.aqi,
        "incidents": state.current_pulse.safety.active_incidents,
    }

    outcome = await evaluate_scenario(request, city_state)
    return outcome.model_dump(mode="json")


@app.post("/api/ask", dependencies=[Depends(rate_limiter(max_requests=15, window_seconds=60))])
async def ask_narad_endpoint(request: AskRequest):
    """
    Ask NARAD a free-form question in natural language (English, Hindi, or
    Telugu) about current city conditions. Grounded in live city pulse +
    latest parliament decision, plus BigQuery historical context when available.
    Rate-limited — each call costs a Gemini request.
    """
    if request.language not in ("english", "hindi", "telugu"):
        raise HTTPException(400, "language must be one of: english, hindi, telugu")

    result = await ask_narad(
        question=request.question,
        language=request.language,
        pulse=state.current_pulse,
        decision=state.latest_decision,
    )
    return result


@app.get("/api/benchmark")
async def get_benchmark(size: int = 100_000):
    """Run a live RAPIDS vs pandas benchmark"""
    size = min(size, 1_000_000)  # cap for safety
    result = await run_benchmark(size)
    return result.model_dump(mode="json")


@app.get("/api/stats")
async def get_stats():
    """Overall system stats for the dashboard"""
    return {
        "app_name": APP_NAME,
        "gpu_active": GPU_AVAILABLE,
        "total_sessions": state.session_count,
        "data_points_collected": len(state.pulse_history),
        "connected_clients": len(state.connected_clients),
        "agents_active": 5,
        "current_health_score": state.current_pulse.overall_health_score if state.current_pulse else None,
    }


# ─── Manual Data Entry (for sectors with no public API) ────────────────────────
#
# Hospitals don't expose real-time bed-availability APIs anywhere in India for
# a hackathon team to integrate against. Rather than leave that data purely
# simulated forever, hospital staff can self-report directly — this becomes
# genuinely real data the moment someone submits it, blended with simulation
# only for the hospitals that haven't reported yet. The same pattern can be
# extended to Safety (police self-reporting incidents) with zero architecture
# changes — just a parallel store + endpoint.

@app.post("/api/manual-data/hospital")
async def submit_hospital_status(
    report: ManualHospitalReport,
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    """
    A hospital self-reports its current status. This becomes real data
    immediately — no external API needed. Triggers an instant broadcast so
    the dashboard reflects it without waiting for the next refresh cycle.
    Requires an API key: this directly affects data other agents and
    officials will rely on, so it must not be open to anonymous submission.
    """
    from backend.data.manual_reports import submit_hospital_report
    saved = submit_hospital_report(report)

    client_ip = request.client.host if request.client else "unknown"
    audit_log_action(
        "hospital_report_submit",
        identity=report.reported_by or f"api_key:{api_key[:6]}...",
        details={
            "hospital_name": report.hospital_name,
            "available_beds": report.available_beds,
            "icu_available": report.icu_available,
        },
        client_ip=client_ip,
    )

    # Refresh city pulse immediately so the new report is reflected right away
    try:
        pulse = await fetch_city_pulse(DEFAULT_CITY)
        state.current_pulse = pulse
        await broadcast(WSMessage(type=WSEventType.CITY_PULSE, payload=pulse.model_dump(mode="json")))
    except Exception as e:
        logger.error(f"Failed to refresh pulse after manual report: {e}")

    return {"status": "received", "hospital_name": saved.hospital_name, "reported_at": saved.reported_at.isoformat()}


@app.get("/api/manual-data/hospital")
async def list_hospital_reports(fresh_only: bool = True):
    """List currently self-reporting hospitals (for an admin/status view) — read-only, no auth required"""
    from backend.data.manual_reports import get_fresh_hospital_reports, get_all_hospital_reports, MANUAL_REPORT_FRESHNESS_MINUTES
    reports = get_fresh_hospital_reports() if fresh_only else get_all_hospital_reports()
    return {
        "reports": [r.model_dump(mode="json") for r in reports],
        "freshness_window_minutes": MANUAL_REPORT_FRESHNESS_MINUTES,
    }


@app.delete("/api/manual-data/hospital/{hospital_name}")
async def remove_hospital_report(
    hospital_name: str,
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    """Remove a hospital's self-report (e.g. to correct a mistaken entry). Requires an API key."""
    from backend.data.manual_reports import delete_hospital_report
    removed = delete_hospital_report(hospital_name)
    if not removed:
        raise HTTPException(404, f"No report found for '{hospital_name}'")

    client_ip = request.client.host if request.client else "unknown"
    audit_log_action(
        "hospital_report_delete",
        identity=f"api_key:{api_key[:6]}...",
        details={"hospital_name": hospital_name},
        client_ip=client_ip,
    )

    # Refresh immediately so the correction is reflected without waiting for
    # the next scheduled refresh cycle — same behavior as submitting a report.
    try:
        pulse = await fetch_city_pulse(DEFAULT_CITY)
        state.current_pulse = pulse
        await broadcast(WSMessage(type=WSEventType.CITY_PULSE, payload=pulse.model_dump(mode="json")))
    except Exception as e:
        logger.error(f"Failed to refresh pulse after report deletion: {e}")

    return {"status": "deleted", "hospital_name": hospital_name}


# ─── WebSocket Endpoint ─────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.connected_clients.add(websocket)
    logger.info(f"Client connected. Total: {len(state.connected_clients)}")

    try:
        # Send current state immediately on connect
        if state.current_pulse:
            await websocket.send_text(
                WSMessage(type=WSEventType.CITY_PULSE, payload=state.current_pulse.model_dump(mode="json")).model_dump_json()
            )
        if state.latest_decision:
            await websocket.send_text(
                WSMessage(type=WSEventType.PARLIAMENT_END, payload=state.latest_decision.model_dump(mode="json")).model_dump_json()
            )

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "trigger_parliament":
                    # SECURITY: this WebSocket path previously bypassed the API
                    # key check applied to the REST /api/parliament/trigger
                    # endpoint entirely — same protection is required here,
                    # since both paths trigger the same costly 5-agent session.
                    from backend.config import NARAD_ADMIN_API_KEY
                    supplied_key = msg.get("api_key", "")
                    if not NARAD_ADMIN_API_KEY or supplied_key != NARAD_ADMIN_API_KEY:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "payload": {"message": "Invalid or missing access key for parliament trigger"}
                        }))
                    else:
                        client_ip = websocket.client.host if websocket.client else "unknown"
                        audit_log_action(
                            "parliament_trigger_ws",
                            identity=f"api_key:{supplied_key[:6]}...",
                            details={"reason": msg.get("reason", "User requested via WebSocket")},
                            client_ip=client_ip,
                        )
                        asyncio.create_task(trigger_parliament(msg.get("reason", "User requested via WebSocket")))
                elif msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        state.connected_clients.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(state.connected_clients)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        state.connected_clients.discard(websocket)


# ─── Static Frontend (production deployment) ───────────────────────────────────

_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

if os.path.isdir(_STATIC_DIR) and os.getenv("SERVE_STATIC", "false").lower() == "true":
    app.mount("/assets", StaticFiles(directory=os.path.join(_STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for any non-API route (client-side routing support)"""
        requested = os.path.join(_STATIC_DIR, full_path)
        if full_path and os.path.isfile(requested):
            return FileResponse(requested)
        return FileResponse(os.path.join(_STATIC_DIR, "index.html"))

    logger.info(f"✅ Serving static frontend from {_STATIC_DIR}")


@app.get("/api/diagnostics/llm")
async def diagnose_llm():
    """
    Test whether the Gemini API key is actually working.
    Hit this endpoint to instantly diagnose why agents might be in fallback mode.
    """
    from backend.config import GEMINI_API_KEY, GEMINI_MODEL
    import os

    diagnosis = {
        "gemini_api_key_present": bool(GEMINI_API_KEY),
        "gemini_api_key_looks_like_placeholder": GEMINI_API_KEY in ("", "your_gemini_api_key_here"),
        "env_GEMINI_API_KEY_set": bool(os.environ.get("GEMINI_API_KEY")),
        "env_GOOGLE_API_KEY_set": bool(os.environ.get("GOOGLE_API_KEY")),
        "model": GEMINI_MODEL,
        "live_call_success": False,
        "error": None,
    }

    if not GEMINI_API_KEY or diagnosis["gemini_api_key_looks_like_placeholder"]:
        diagnosis["error"] = (
            "GEMINI_API_KEY is missing or still the placeholder value. "
            "Edit your .env file and set GEMINI_API_KEY to a real key from "
            "https://aistudio.google.com/app/apikey, then restart the backend."
        )
        return diagnosis

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL, contents="Reply with exactly: OK"
        )
        diagnosis["live_call_success"] = True
        diagnosis["sample_response"] = response.text
    except Exception as e:
        diagnosis["error"] = f"{type(e).__name__}: {str(e)}"

    return diagnosis


@app.get("/api/diagnostics/traffic")
async def diagnose_traffic():
    """
    Test whether live Google Maps traffic data is working, or if the system
    is running on realistic simulation instead.
    """
    from backend.config import GOOGLE_MAPS_API_KEY
    from backend.data.live_feeds import _fetch_traffic_google_maps

    diagnosis = {
        "google_maps_api_key_present": bool(GOOGLE_MAPS_API_KEY),
        "live_traffic_working": False,
        "mode": "simulation",
        "error": None,
    }

    if not GOOGLE_MAPS_API_KEY:
        diagnosis["error"] = (
            "GOOGLE_MAPS_API_KEY is not set — traffic data is realistic simulation, "
            "not live. Get a key at https://console.cloud.google.com/google/maps-apis/credentials "
            "and add it to .env as GOOGLE_MAPS_API_KEY to enable real live traffic."
        )
        return diagnosis

    try:
        result = await _fetch_traffic_google_maps()
        diagnosis["live_traffic_working"] = True
        diagnosis["mode"] = "live_google_maps"
        diagnosis["sample_congestion_level"] = result.congestion_level
        diagnosis["sample_affected_zones"] = result.affected_zones
    except Exception as e:
        diagnosis["error"] = f"{type(e).__name__}: {str(e)}"

    return diagnosis


@app.get("/api/diagnostics/bigquery")
async def diagnose_bigquery():
    """
    Test whether BigQuery is actually connected and storing data, or if the
    system is running on the in-memory fallback buffer instead.
    """
    status = bigquery_store.get_status()
    if status["available"]:
        status["note"] = (
            f"Connected. Historical pulse + parliament decisions are being "
            f"persisted to `{status['project']}.{status['dataset']}` — "
            f"queryable across restarts, unlike the in-memory buffer."
        )
    else:
        status["note"] = (
            "Not connected — history endpoints are serving the in-memory "
            "buffer (last ~200 pulse points / 20 decisions, reset on restart). "
            "To enable: set GCP_PROJECT_ID to a real project with the BigQuery "
            "API enabled, and ensure Application Default Credentials are "
            "available (gcloud auth application-default login locally, or the "
            "Cloud Run service account in production)."
        )
    return status


if __name__ == "__main__":
    import uvicorn
    from backend.config import PORT
    uvicorn.run("backend.main:app", host="0.0.0.0", port=PORT, reload=True)
