"""
Tests for backend/models/schemas.py — verifies input validation actually
rejects bad data. These are the constraints that stand between an attacker
and a corrupted hospital capacity record.
"""
import pytest
from pydantic import ValidationError

from backend.models.schemas import ManualHospitalReport, ScenarioRequest, AskRequest


class TestManualHospitalReportValidation:
    def test_valid_report_accepted(self):
        report = ManualHospitalReport(
            hospital_name="Test Hospital", available_beds=20, icu_available=2
        )
        assert report.hospital_name == "Test Hospital"
        assert report.available_beds == 20

    def test_negative_beds_rejected(self):
        with pytest.raises(ValidationError):
            ManualHospitalReport(hospital_name="X", available_beds=-1, icu_available=1)

    def test_negative_icu_rejected(self):
        with pytest.raises(ValidationError):
            ManualHospitalReport(hospital_name="X", available_beds=10, icu_available=-5)

    def test_excessive_beds_rejected(self):
        with pytest.raises(ValidationError):
            ManualHospitalReport(hospital_name="X", available_beds=999999, icu_available=1)

    def test_empty_hospital_name_rejected(self):
        with pytest.raises(ValidationError):
            ManualHospitalReport(hospital_name="", available_beds=10, icu_available=1)

    def test_oversized_hospital_name_rejected(self):
        with pytest.raises(ValidationError):
            ManualHospitalReport(hospital_name="X" * 500, available_beds=10, icu_available=1)

    def test_negative_wait_time_rejected(self):
        with pytest.raises(ValidationError):
            ManualHospitalReport(
                hospital_name="X", available_beds=10, icu_available=1,
                emergency_wait_minutes=-10
            )

    def test_reported_by_optional(self):
        report = ManualHospitalReport(hospital_name="X", available_beds=10, icu_available=1)
        assert report.reported_by is None

    def test_oversized_reported_by_rejected(self):
        with pytest.raises(ValidationError):
            ManualHospitalReport(
                hospital_name="X", available_beds=10, icu_available=1,
                reported_by="Y" * 500
            )


class TestScenarioRequestValidation:
    def test_valid_scenario_accepted(self):
        req = ScenarioRequest(
            name="Test", description="Test scenario",
            parameters={"traffic_delta": 10}, scenario_count=500
        )
        assert req.scenario_count == 500

    def test_excessive_scenario_count_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioRequest(
                name="Test", description="Test",
                parameters={}, scenario_count=999999
            )

    def test_oversized_name_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioRequest(
                name="X" * 1000, description="Test",
                parameters={}, scenario_count=100
            )


class TestAskRequestValidation:
    def test_valid_question_accepted(self):
        req = AskRequest(question="What is the AQI?", language="english")
        assert req.language == "english"

    def test_empty_question_rejected(self):
        with pytest.raises(ValidationError):
            AskRequest(question="")

    def test_oversized_question_rejected(self):
        with pytest.raises(ValidationError):
            AskRequest(question="X" * 5000)

    def test_default_language_is_english(self):
        req = AskRequest(question="Test")
        assert req.language == "english"
