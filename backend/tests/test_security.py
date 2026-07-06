import pytest
from fastapi import HTTPException
from backend.security import verify_api_key

def test_verify_api_key_valid(monkeypatch):
    monkeypatch.setenv("NARAD_ADMIN_API_KEY", "test-key-123")
    # Actually backend config reads this. So we patch config.
    from backend import config
    monkeypatch.setattr(config, "NARAD_ADMIN_API_KEY", "test-key-123")
    
    assert verify_api_key("test-key-123") == "test-key-123"

def test_verify_api_key_invalid(monkeypatch):
    from backend import config
    monkeypatch.setattr(config, "NARAD_ADMIN_API_KEY", "test-key-123")
    
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key("wrong-key")
    
    assert exc_info.value.status_code == 401
