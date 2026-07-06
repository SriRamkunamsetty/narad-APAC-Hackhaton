import pytest
from backend.data.manual_reports import submit_hospital_report, get_fresh_hospital_reports, delete_hospital_report
from backend.models.schemas import ManualHospitalReport

def test_manual_hospital_reports_lifecycle():
    report = ManualHospitalReport(
        hospital_name="Test Hospital",
        available_beds=10,
        icu_available=2,
        ambulances_active=1,
        emergency_wait_minutes=15,
        reported_by="Staff"
    )
    
    # Submit
    saved = submit_hospital_report(report)
    assert saved.hospital_name == "Test Hospital"
    
    # Get
    fresh = get_fresh_hospital_reports()
    assert any(r.hospital_name == "Test Hospital" for r in fresh)
    
    # Delete
    assert delete_hospital_report("Test Hospital") is True
    
    # Verify deletion
    fresh_after = get_fresh_hospital_reports()
    assert not any(r.hospital_name == "Test Hospital" for r in fresh_after)
