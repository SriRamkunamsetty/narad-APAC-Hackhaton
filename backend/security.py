"""
NARAD - Security Layer

Baseline hardening for state-changing and cost-incurring endpoints:
  - API key authentication (X-API-Key header) for write operations — fails
    CLOSED if no key is configured, rather than silently allowing open access
  - Simple in-memory rate limiting per client IP, for LLM/compute-cost endpoints
  - Structured audit logging for every authenticated write action

═══════════════════════════════════════════════════════════════════════════
READ THIS BEFORE ANY REAL GOVERNMENT OR PRODUCTION DEPLOYMENT
═══════════════════════════════════════════════════════════════════════════
This module raises the floor from "wide open to the internet" to "requires
a shared secret" — it is a genuine improvement, but it is NOT equivalent to
real production security. Specifically:

1. A single shared API key means every hospital/operator uses the SAME
   credential. There is no way to know WHICH person submitted a report, only
   that someone with the key did. Real accountability requires per-user
   authentication — Firebase Authentication or Google Cloud Identity Platform
   is the natural fit here (same ecosystem, minimal extra infra) and should
   replace this before real hospital staff are onboarded.

2. The rate limiter is in-memory and per-instance. It works correctly on a
   single Cloud Run instance but does NOT synchronize across multiple
   replicas under load. Real production traffic should be rate-limited at
   the infrastructure layer instead — Google Cloud Armor, sitting in front
   of Cloud Run, is the standard pattern and doesn't have this limitation.

3. Nothing here has been through a real security audit. Before any Indian
   government body relies on this system operationally, it should go through
   a formal VAPT (Vulnerability Assessment and Penetration Testing) engagement
   with a CERT-In empanelled auditor — this is generally a mandatory
   requirement for government-facing IT systems in India, not optional
   due-diligence.

Treat everything in this file as "reasonable hardening for a pilot/demo",
not "certified secure for production."
"""
import time
import logging
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from fastapi import Header, HTTPException, Request

from backend.config import NARAD_ADMIN_API_KEY

logger = logging.getLogger("narad.security")


# ─── API Key Authentication ───────────────────────────────────────────────────

async def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> str:
    """
    FastAPI dependency: require a valid API key for state-changing endpoints.
    Fails CLOSED — if no key is configured server-side at all, writes are
    refused entirely rather than silently left open.
    """
    if not NARAD_ADMIN_API_KEY:
        raise HTTPException(
            503,
            "Write operations are disabled: NARAD_ADMIN_API_KEY is not configured "
            "on the server. Set it in the environment before allowing any "
            "data-mutating requests."
        )
    if not x_api_key or x_api_key != NARAD_ADMIN_API_KEY:
        raise HTTPException(401, "Invalid or missing X-API-Key header")
    return x_api_key


# ─── Simple In-Memory Rate Limiter ────────────────────────────────────────────
# See module docstring: per-instance only, not a substitute for Cloud Armor
# in a real multi-replica production deployment.

_request_log: Dict[str, Deque[float]] = defaultdict(deque)


def rate_limiter(max_requests: int, window_seconds: int):
    """Returns a FastAPI dependency enforcing max_requests per window_seconds per client IP"""
    async def _check(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = _request_log[client_ip]

        while window and window[0] < now - window_seconds:
            window.popleft()

        if len(window) >= max_requests:
            raise HTTPException(
                429,
                f"Rate limit exceeded: max {max_requests} requests per {window_seconds}s. Try again shortly."
            )

        window.append(now)
    return _check


# ─── Audit Logging ─────────────────────────────────────────────────────────────

def audit_log_action(action: str, identity: str, details: dict, client_ip: str = "unknown") -> None:
    """
    Structured audit log for every authenticated write action. Always logged
    to stdout/Cloud Logging; also persisted to BigQuery when available for
    real queryable audit history.
    """
    logger.info(f"AUDIT | action={action} | identity={identity} | ip={client_ip} | details={details}")
    try:
        from backend.data import bigquery_store
        bigquery_store.insert_audit_log(action=action, identity=identity, details=details, client_ip=client_ip)
    except Exception as e:
        logger.error(f"Audit log BigQuery insert failed (logged above regardless): {e}")
