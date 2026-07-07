"""
Tests for backend/security.py — API key auth and rate limiting.
Given today's discovery of a real WebSocket auth bypass, this module gets
the most thorough testing in the suite: security code that isn't tested is
security code you're just hoping works.
"""
import asyncio
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from backend.security import verify_api_key, rate_limiter, _request_log


class TestVerifyApiKey:
    async def test_fails_closed_when_no_key_configured(self):
        """If NARAD_ADMIN_API_KEY is unset server-side, writes must be refused
        entirely — not silently allowed through."""
        with patch("backend.config.NARAD_ADMIN_API_KEY", ""):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(x_api_key="anything")
            assert exc_info.value.status_code == 503

    async def test_rejects_missing_header(self):
        with patch("backend.config.NARAD_ADMIN_API_KEY", "secret123"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(x_api_key=None)
            assert exc_info.value.status_code == 401

    async def test_rejects_wrong_key(self):
        with patch("backend.config.NARAD_ADMIN_API_KEY", "secret123"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(x_api_key="wrong-key")
            assert exc_info.value.status_code == 401

    async def test_accepts_correct_key(self):
        with patch("backend.config.NARAD_ADMIN_API_KEY", "secret123"):
            result = await verify_api_key(x_api_key="secret123")
            assert result == "secret123"

    async def test_empty_string_key_is_rejected_even_if_header_present(self):
        """An empty-string X-API-Key header should not bypass auth."""
        with patch("backend.config.NARAD_ADMIN_API_KEY", "secret123"):
            with pytest.raises(HTTPException):
                await verify_api_key(x_api_key="")


class TestRateLimiter:
    def setup_method(self):
        # Clear rate limiter state between tests so they don't interfere
        _request_log.clear()

    async def test_allows_requests_under_limit(self):
        check = rate_limiter(max_requests=5, window_seconds=60)
        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"

        for _ in range(5):
            await check(mock_request)  # should not raise

    async def test_blocks_requests_over_limit(self):
        check = rate_limiter(max_requests=3, window_seconds=60)
        mock_request = MagicMock()
        mock_request.client.host = "5.6.7.8"

        for _ in range(3):
            await check(mock_request)

        with pytest.raises(HTTPException) as exc_info:
            await check(mock_request)
        assert exc_info.value.status_code == 429

    async def test_different_ips_have_independent_limits(self):
        check = rate_limiter(max_requests=2, window_seconds=60)
        req_a = MagicMock()
        req_a.client.host = "1.1.1.1"
        req_b = MagicMock()
        req_b.client.host = "2.2.2.2"

        await check(req_a)
        await check(req_a)
        # req_a is now at its limit, but req_b should be unaffected
        await check(req_b)  # should not raise

    async def test_window_expires_old_requests(self):
        check = rate_limiter(max_requests=1, window_seconds=1)
        mock_request = MagicMock()
        mock_request.client.host = "9.9.9.9"

        await check(mock_request)
        with pytest.raises(HTTPException):
            await check(mock_request)

        await asyncio.sleep(1.1)
        await check(mock_request)  # should not raise — window has passed
