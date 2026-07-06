"""
NARAD - Manual Data Entry Store

For domains where no public real-time API exists (hospital capacity, and
potentially safety/police data in future), NARAD lets the actual source of
truth — hospital staff, in this case — self-report their own status directly.

This is a genuine third data tier, prioritized as:
    1. Live external API  (when one exists)
    2. Manual human report (fresh, i.e. recently submitted)
    3. Realistic simulation (fallback when neither exists)

Architecture note: this uses in-memory storage, which is sufficient for a
single Cloud Run instance / hackathon demo, but does NOT persist across
instance restarts or scale across multiple Cloud Run replicas. For a real
production deployment, swap this store for Firestore (fits natively into
the Google Cloud stack already in use) — the public functions below
(submit_report / get_fresh_reports / get_all_reports) are the only surface
area that would need to change; callers are unaffected.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from backend.models.schemas import ManualHospitalReport
from backend.data import bigquery_store

logger = logging.getLogger("narad.manual_reports")

# hospital_name -> latest report
_hospital_reports: Dict[str, ManualHospitalReport] = {}

# How long a manual report is trusted before it's considered stale and
# the system falls back to simulation for that hospital.
MANUAL_REPORT_FRESHNESS_MINUTES = 120


def submit_hospital_report(report: ManualHospitalReport) -> ManualHospitalReport:
    """Store or overwrite a hospital's self-reported status"""
    _hospital_reports[report.hospital_name.strip()] = report
    if bigquery_store.BIGQUERY_AVAILABLE:
        bigquery_store.insert_hospital_report(report)
    logger.info(f"📋 Manual report received: {report.hospital_name} — "
                f"{report.available_beds} beds, {report.icu_available} ICU")
    return report


def get_fresh_hospital_reports(max_age_minutes: int = MANUAL_REPORT_FRESHNESS_MINUTES) -> List[ManualHospitalReport]:
    """Return only reports submitted within the freshness window"""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    
    if bigquery_store.BIGQUERY_AVAILABLE:
        bq_reports = bigquery_store.query_hospital_reports()
        if bq_reports:
            fresh = [r for r in bq_reports if r.reported_at >= cutoff]
            return sorted(fresh, key=lambda r: r.reported_at, reverse=True)
            
    fresh = [r for r in _hospital_reports.values() if r.reported_at >= cutoff]
    return sorted(fresh, key=lambda r: r.reported_at, reverse=True)


def get_all_hospital_reports() -> List[ManualHospitalReport]:
    """Return every stored report, fresh or stale (for an admin/status view)"""
    if bigquery_store.BIGQUERY_AVAILABLE:
        bq_reports = bigquery_store.query_hospital_reports()
        if bq_reports:
            return sorted(bq_reports, key=lambda r: r.reported_at, reverse=True)
            
    return sorted(_hospital_reports.values(), key=lambda r: r.reported_at, reverse=True)


def delete_hospital_report(hospital_name: str) -> bool:
    """Remove a hospital's report (e.g. to correct a mistaken entry)"""
    mem_removed = _hospital_reports.pop(hospital_name.strip(), None) is not None
    if bigquery_store.BIGQUERY_AVAILABLE:
        bq_removed = bigquery_store.delete_hospital_report(hospital_name.strip())
        return mem_removed or bq_removed
    return mem_removed
