import pytest
from pydantic import ValidationError
from backend.models.schemas import ManualHospitalReport, AskRequest, Severity

def test_manual_hospital_report_validation():
    # Valid
    report = ManualHospitalReport(
        hospital_name="Test Hospital",
        available_beds=10,
        icu_available=2,
        ambulances_active=1,
        emergency_wait_minutes=15,
        reported_by="Staff"
    )
    assert report.hospital_name == "Test Hospital"

    # Invalid - negative beds
    with pytest.raises(ValidationError):
        ManualHospitalReport(
            hospital_name="Test Hospital",
            available_beds=-10,
            icu_available=2,
            ambulances_active=1,
            emergency_wait_minutes=15,
            reported_by="Staff"
        )

def test_ask_request_validation():
    # Valid
    req = AskRequest(question="What is the weather?", language="english")
    assert req.language == "english"

    # Valid
    req2 = AskRequest(question="What is the weather?")
    assert req2.language == "english"

def test_severity_enum():
    assert Severity.LOW.value == "low"
    assert Severity.CRITICAL.value == "critical"
