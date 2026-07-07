"""
Tests for backend/data/manual_reports.py — the hospital self-reporting
store, including the BigQuery write-through/read-merge logic added for
cross-instance consistency.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from backend.data import manual_reports
from backend.models.schemas import ManualHospitalReport


@pytest.fixture(autouse=True)
def clean_store():
    """Ensure each test starts with an empty in-memory store"""
    manual_reports._hospital_reports.clear()
    yield
    manual_reports._hospital_reports.clear()


class TestLocalStoreOnly:
    """Behavior when BigQuery is unavailable — must work standalone"""

    def test_submit_and_retrieve(self):
        with patch("backend.data.bigquery_store.BIGQUERY_AVAILABLE", False):
            manual_reports.submit_hospital_report(
                ManualHospitalReport(hospital_name="Test A", available_beds=10, icu_available=1)
            )
            reports = manual_reports.get_fresh_hospital_reports()
            assert len(reports) == 1
            assert reports[0].hospital_name == "Test A"

    def test_delete_removes_report(self):
        with patch("backend.data.bigquery_store.BIGQUERY_AVAILABLE", False):
            manual_reports.submit_hospital_report(
                ManualHospitalReport(hospital_name="Test B", available_beds=5, icu_available=0)
            )
            assert manual_reports.delete_hospital_report("Test B") is True
            assert len(manual_reports.get_fresh_hospital_reports()) == 0

    def test_delete_nonexistent_returns_false(self):
        assert manual_reports.delete_hospital_report("Nonexistent") is False

    def test_stale_reports_excluded_from_fresh(self):
        stale_report = ManualHospitalReport(
            hospital_name="Stale Hospital", available_beds=5, icu_available=0
        )
        # Manually backdate it past the freshness window
        stale_report.reported_at = datetime.now(timezone.utc) - timedelta(hours=5)
        manual_reports._hospital_reports["Stale Hospital"] = stale_report

        with patch("backend.data.bigquery_store.BIGQUERY_AVAILABLE", False):
            fresh = manual_reports.get_fresh_hospital_reports(max_age_minutes=120)
            assert len(fresh) == 0

    def test_submission_overwrites_previous_report_for_same_hospital(self):
        with patch("backend.data.bigquery_store.BIGQUERY_AVAILABLE", False):
            manual_reports.submit_hospital_report(
                ManualHospitalReport(hospital_name="X", available_beds=10, icu_available=1)
            )
            manual_reports.submit_hospital_report(
                ManualHospitalReport(hospital_name="X", available_beds=3, icu_available=0)
            )
            reports = manual_reports.get_fresh_hospital_reports()
            assert len(reports) == 1
            assert reports[0].available_beds == 3


class TestBigQueryMerge:
    """Behavior when BigQuery IS available — cross-instance consistency"""

    def test_bigquery_write_through_called_on_submit(self):
        with patch("backend.data.bigquery_store.insert_hospital_report") as mock_insert:
            manual_reports.submit_hospital_report(
                ManualHospitalReport(hospital_name="Y", available_beds=8, icu_available=1)
            )
            mock_insert.assert_called_once()
            _, kwargs = mock_insert.call_args
            assert kwargs["hospital_name"] == "Y"
            assert kwargs["available_beds"] == 8

    def test_bigquery_failure_does_not_break_local_submit(self):
        """A BigQuery outage must not prevent the local write from succeeding"""
        with patch("backend.data.bigquery_store.insert_hospital_report", side_effect=Exception("BQ down")):
            manual_reports.submit_hospital_report(
                ManualHospitalReport(hospital_name="Z", available_beds=6, icu_available=1)
            )
            # Local cache should still have it despite BigQuery failing
            with patch("backend.data.bigquery_store.BIGQUERY_AVAILABLE", False):
                reports = manual_reports.get_fresh_hospital_reports()
                assert any(r.hospital_name == "Z" for r in reports)

    def test_remote_report_merged_into_results(self):
        """A report that ONLY exists in BigQuery (submitted to a different
        instance) must still show up in get_fresh_hospital_reports()."""
        remote_row = {
            "hospital_name": "Remote Hospital",
            "available_beds": 15,
            "icu_available": 2,
            "ambulances_active": 3,
            "emergency_wait_minutes": 20.0,
            "reported_by": "Other Instance",
            "reported_at": datetime.now(timezone.utc),
        }
        with patch("backend.data.bigquery_store.BIGQUERY_AVAILABLE", True), \
             patch("backend.data.bigquery_store.query_fresh_hospital_reports", return_value=[remote_row]):
            reports = manual_reports.get_fresh_hospital_reports()
            names = [r.hospital_name for r in reports]
            assert "Remote Hospital" in names

    def test_bigquery_read_failure_falls_back_to_local_only(self):
        with patch("backend.data.bigquery_store.BIGQUERY_AVAILABLE", False):
            manual_reports.submit_hospital_report(
                ManualHospitalReport(hospital_name="Local Only", available_beds=4, icu_available=0)
            )
        with patch("backend.data.bigquery_store.BIGQUERY_AVAILABLE", True), \
             patch("backend.data.bigquery_store.query_fresh_hospital_reports", side_effect=Exception("BQ error")):
            reports = manual_reports.get_fresh_hospital_reports()
            # Should not crash, and local report should still be present
            assert any(r.hospital_name == "Local Only" for r in reports)
