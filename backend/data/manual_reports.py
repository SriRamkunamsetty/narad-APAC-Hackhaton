"""
NARAD - Manual Data Entry Store

For domains where no public real-time API exists (hospital capacity, and
potentially safety/police data in future), NARAD lets the actual source of
truth — hospital staff, in this case — self-report their own status directly.

This is a genuine third data tier, prioritized as:
    1. Live external API  (when one exists)
    2. Manual human report (fresh, i.e. recently submitted)
    3. Realistic simulation (fallback when neither exists)

Cross-instance consistency: reports are written through to BigQuery on
submit (when available) and reads merge the in-memory cache with BigQuery
results. Without this, a report submitted to one Cloud Run instance would
be invisible from any other instance — a real correctness gap the moment
Cloud Run scales beyond a single replica, which is the entire point of
using Cloud Run. Without BigQuery configured, this falls back to in-memory
only, correct for a single instance but not for real horizontal scaling —
that limitation is surfaced honestly via /api/diagnostics/bigquery rather
than silently accepted.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from backend.models.schemas import ManualHospitalReport

logger = logging.getLogger("narad.manual_reports")

# hospital_name -> latest report (fast local cache; BigQuery is the
# cross-instance source of truth when configured)
_hospital_reports: Dict[str, ManualHospitalReport] = {}

# How long a manual report is trusted before it's considered stale and
# the system falls back to simulation for that hospital.
MANUAL_REPORT_FRESHNESS_MINUTES = 120


def submit_hospital_report(report: ManualHospitalReport) -> ManualHospitalReport:
    """Store a hospital's self-reported status locally, and write through to
    BigQuery so every Cloud Run instance can see it, not just this one."""
    _hospital_reports[report.hospital_name.strip()] = report
    logger.info(f"📋 Manual report received: {report.hospital_name} — "
                f"{report.available_beds} beds, {report.icu_available} ICU")

    try:
        from backend.data import bigquery_store
        bigquery_store.insert_hospital_report(
            hospital_name=report.hospital_name,
            available_beds=report.available_beds,
            icu_available=report.icu_available,
            ambulances_active=report.ambulances_active,
            emergency_wait_minutes=report.emergency_wait_minutes,
            reported_by=report.reported_by,
            reported_at=report.reported_at,
        )
    except Exception as e:
        logger.error(f"BigQuery write-through failed for hospital report (non-fatal, "
                     f"local cache still updated): {e}")

    return report


def get_fresh_hospital_reports(max_age_minutes: int = MANUAL_REPORT_FRESHNESS_MINUTES) -> List[ManualHospitalReport]:
    """
    Return the latest fresh report per hospital, merging the local in-memory
    cache with BigQuery (if available) so reports submitted to OTHER Cloud
    Run instances are visible here too. Local cache wins on conflict only if
    it's strictly newer than the BigQuery-sourced entry (handles the brief
    window before a just-submitted report has been queried back).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    merged: Dict[str, ManualHospitalReport] = {
        name: r for name, r in _hospital_reports.items() if r.reported_at >= cutoff
    }

    try:
        from backend.data import bigquery_store
        if bigquery_store.BIGQUERY_AVAILABLE:
            for row in bigquery_store.query_fresh_hospital_reports(max_age_minutes):
                try:
                    remote = ManualHospitalReport(
                        hospital_name=row["hospital_name"],
                        available_beds=row["available_beds"],
                        icu_available=row["icu_available"],
                        ambulances_active=row["ambulances_active"],
                        emergency_wait_minutes=row["emergency_wait_minutes"],
                        reported_by=row.get("reported_by") or None,
                        reported_at=row["reported_at"],
                    )
                except Exception:
                    continue
                existing = merged.get(remote.hospital_name)
                if existing is None or remote.reported_at >= existing.reported_at:
                    merged[remote.hospital_name] = remote
    except Exception as e:
        logger.error(f"BigQuery read-merge failed for hospital reports (non-fatal, "
                     f"serving local cache only): {e}")

    return sorted(merged.values(), key=lambda r: r.reported_at, reverse=True)


def get_all_hospital_reports() -> List[ManualHospitalReport]:
    """Return every stored report, fresh or stale (for an admin/status view) — local cache only"""
    return sorted(_hospital_reports.values(), key=lambda r: r.reported_at, reverse=True)


def delete_hospital_report(hospital_name: str) -> bool:
    """
    Remove a hospital's report from the local cache. Note: this does NOT
    delete the historical rows from BigQuery (by design — audit history is
    preserved), so on a multi-instance deployment a withdrawn report may
    still surface from BigQuery until its freshness window naturally
    expires. This is a known limitation worth closing with a proper
    tombstone/deletion-marker row if withdrawal needs to be instant across
    all instances.
    """
    return _hospital_reports.pop(hospital_name.strip(), None) is not None
