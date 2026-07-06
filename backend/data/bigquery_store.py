"""
NARAD - BigQuery Storage Layer

Replaces in-memory pulse_history / decision_history lists with real,
persistent, queryable storage. This satisfies the "Google Cloud data layer"
requirement (PS2) and unlocks genuine historical analysis — trend queries,
similar-past-incident lookups for the "Ask NARAD" RAG interface, and
eventually BigQuery ML forecasting — none of which are possible with an
in-memory list that resets on every Cloud Run cold start.

Design: every function here degrades gracefully. If the `google-cloud-bigquery`
package isn't installed, or no GCP project/credentials are configured, or any
call fails (e.g. no permissions), BIGQUERY_AVAILABLE flips to False and every
write/read becomes a safe no-op — the rest of NARAD (in-memory fallback lists
in main.py) keeps working exactly as before. Nothing about this is silently
faked: /api/diagnostics/bigquery reports the real status.
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from backend.config import GCP_PROJECT_ID, BIGQUERY_DATASET
from backend.models.schemas import CityPulse, ParliamentDecision

logger = logging.getLogger("narad.bigquery")

BIGQUERY_AVAILABLE = False
_client = None
_init_error: Optional[str] = None

_PULSE_TABLE = "pulse_history"
_DECISION_TABLE = "parliament_decisions"
_AUDIT_TABLE = "audit_log"

_PULSE_SCHEMA_SQL = """
    timestamp TIMESTAMP,
    city STRING,
    aqi INT64,
    congestion FLOAT64,
    hospital_load FLOAT64,
    incidents INT64,
    overall_health_score FLOAT64,
    hospitals_source STRING,
    traffic_source STRING,
    raw_json STRING
"""

_DECISION_SCHEMA_SQL = """
    session_id STRING,
    timestamp TIMESTAMP,
    city STRING,
    trigger STRING,
    overall_urgency STRING,
    confidence_score FLOAT64,
    consensus STRING,
    processing_time_ms FLOAT64,
    causal_chain_json STRING,
    dissent_log_json STRING,
    action_plan_json STRING,
    affected_zones_json STRING,
    raw_json STRING
"""

_AUDIT_SCHEMA_SQL = """
    timestamp TIMESTAMP,
    action STRING,
    identity STRING,
    client_ip STRING,
    details_json STRING
"""


def init_bigquery() -> None:
    """
    Attempt to connect to BigQuery and ensure the dataset/tables exist.
    Called once at app startup. Safe to call even with no credentials —
    failure just leaves BIGQUERY_AVAILABLE=False and logs why.
    """
    global BIGQUERY_AVAILABLE, _client, _init_error

    if not GCP_PROJECT_ID:
        _init_error = "GCP_PROJECT_ID not set"
        logger.info(f"⚠️  BigQuery disabled: {_init_error}")
        return

    try:
        from google.cloud import bigquery
        _client = bigquery.Client(project=GCP_PROJECT_ID)

        dataset_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        _client.create_dataset(dataset, exists_ok=True)

        for table_name, schema_sql in [
            (_PULSE_TABLE, _PULSE_SCHEMA_SQL),
            (_DECISION_TABLE, _DECISION_SCHEMA_SQL),
            (_AUDIT_TABLE, _AUDIT_SCHEMA_SQL),
        ]:
            table_id = f"{dataset_id}.{table_name}"
            _client.query(f"""
                CREATE TABLE IF NOT EXISTS `{table_id}` ({schema_sql})
                PARTITION BY DATE(timestamp)
            """).result()

        BIGQUERY_AVAILABLE = True
        logger.info(f"✅ BigQuery connected — dataset `{dataset_id}` ready")

    except Exception as e:
        _init_error = f"{type(e).__name__}: {e}"
        BIGQUERY_AVAILABLE = False
        logger.warning(f"⚠️  BigQuery unavailable, using in-memory fallback only. Reason: {_init_error}")


def get_status() -> Dict[str, Any]:
    """For the diagnostics endpoint — honest report of BigQuery connection state"""
    return {
        "available": BIGQUERY_AVAILABLE,
        "project": GCP_PROJECT_ID or None,
        "dataset": BIGQUERY_DATASET,
        "error": _init_error,
    }


def insert_pulse_snapshot(pulse: CityPulse) -> None:
    """Stream a city pulse snapshot into BigQuery. No-op if unavailable."""
    if not BIGQUERY_AVAILABLE or _client is None:
        return
    try:
        table_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{_PULSE_TABLE}"
        row = {
            "timestamp": pulse.timestamp.isoformat(),
            "city": pulse.city,
            "aqi": pulse.aqi.aqi,
            "congestion": pulse.traffic.congestion_level,
            "hospital_load": pulse.hospitals.capacity_percent,
            "incidents": pulse.safety.active_incidents,
            "overall_health_score": pulse.overall_health_score,
            "hospitals_source": pulse.data_sources.get("hospitals", "simulated"),
            "traffic_source": pulse.data_sources.get("traffic", "simulated"),
            "raw_json": pulse.model_dump_json(),
        }
        errors = _client.insert_rows_json(table_id, [row])
        if errors:
            logger.error(f"BigQuery pulse insert errors: {errors}")
    except Exception as e:
        logger.error(f"BigQuery pulse insert failed: {e}")


def insert_parliament_decision(decision: ParliamentDecision) -> None:
    """Stream a parliament decision into BigQuery. No-op if unavailable."""
    if not BIGQUERY_AVAILABLE or _client is None:
        return
    try:
        table_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{_DECISION_TABLE}"
        row = {
            "session_id": decision.session_id,
            "timestamp": decision.timestamp.isoformat(),
            "city": decision.city,
            "trigger": decision.trigger,
            "overall_urgency": decision.overall_urgency.value,
            "confidence_score": decision.confidence_score,
            "consensus": decision.consensus,
            "processing_time_ms": decision.processing_time_ms,
            "causal_chain_json": json.dumps(decision.causal_chain),
            "dissent_log_json": json.dumps(decision.dissent_log),
            "action_plan_json": json.dumps(decision.action_plan),
            "affected_zones_json": json.dumps(decision.affected_zones),
            "raw_json": decision.model_dump_json(),
        }
        errors = _client.insert_rows_json(table_id, [row])
        if errors:
            logger.error(f"BigQuery decision insert errors: {errors}")
    except Exception as e:
        logger.error(f"BigQuery decision insert failed: {e}")


def query_pulse_history(hours: int = 24, city: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query recent pulse history from BigQuery. Returns [] if unavailable."""
    if not BIGQUERY_AVAILABLE or _client is None:
        return []
    try:
        table_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{_PULSE_TABLE}"
        city_filter = f'AND city = "{city}"' if city else ""
        query = f"""
            SELECT timestamp, city, aqi, congestion, hospital_load, incidents, overall_health_score
            FROM `{table_id}`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {int(hours)} HOUR)
            {city_filter}
            ORDER BY timestamp ASC
            LIMIT 2000
        """
        rows = _client.query(query).result()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"BigQuery pulse query failed: {e}")
        return []


def query_recent_decisions(limit: int = 20, city: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query recent parliament decisions from BigQuery. Returns [] if unavailable."""
    if not BIGQUERY_AVAILABLE or _client is None:
        return []
    try:
        table_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{_DECISION_TABLE}"
        city_filter = f'WHERE city = "{city}"' if city else ""
        query = f"""
            SELECT * FROM `{table_id}`
            {city_filter}
            ORDER BY timestamp DESC
            LIMIT {int(limit)}
        """
        rows = _client.query(query).result()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"BigQuery decision query failed: {e}")
        return []


def query_similar_past_decisions(overall_urgency: str, city: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Simple similarity lookup for the 'Ask NARAD' RAG context: most recent past
    decisions that shared the same urgency level. This is a lightweight proxy
    for full semantic similarity search — a real production version would use
    BigQuery's native VECTOR_SEARCH over Gemini text embeddings of `consensus`,
    which is a natural next upgrade with this same table already in place.
    """
    if not BIGQUERY_AVAILABLE or _client is None:
        return []
    try:
        table_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{_DECISION_TABLE}"
        query = f"""
            SELECT session_id, timestamp, trigger, consensus, overall_urgency, action_plan_json
            FROM `{table_id}`
            WHERE city = "{city}" AND overall_urgency = "{overall_urgency}"
            ORDER BY timestamp DESC
            LIMIT {int(limit)}
        """
        rows = _client.query(query).result()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"BigQuery similarity query failed: {e}")
        return []


def insert_audit_log(action: str, identity: str, details: Dict[str, Any], client_ip: str = "unknown") -> None:
    """
    Persist a security audit event (data submission, deletion, manual
    parliament trigger, etc). No-op if BigQuery is unavailable — the caller
    (backend/security.py) already logs to stdout/Cloud Logging regardless,
    so nothing is silently lost even without BigQuery configured.
    """
    if not BIGQUERY_AVAILABLE or _client is None:
        return
    try:
        table_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{_AUDIT_TABLE}"
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "identity": identity,
            "client_ip": client_ip,
            "details_json": json.dumps(details, default=str),
        }
        errors = _client.insert_rows_json(table_id, [row])
        if errors:
            logger.error(f"BigQuery audit log insert errors: {errors}")
    except Exception as e:
        logger.error(f"BigQuery audit log insert failed: {e}")
