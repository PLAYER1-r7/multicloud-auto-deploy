"""Unit tests for helper logic in app.main."""

from collections import deque
from unittest.mock import patch

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse, Response

import app.main as main_module


def _make_request(
    path: str, headers: dict | None = None, client_host: str = "127.0.0.1"
) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in (headers or {}).items()
        ],
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


class TestGetClientIp:
    def test_get_client_ip_from_x_forwarded_for(self):
        request = _make_request(
            "/api/health", {"x-forwarded-for": "203.0.113.1, 10.0.0.1"}
        )
        assert main_module._get_client_ip(request) == "203.0.113.1"

    def test_get_client_ip_from_client_host(self):
        request = _make_request("/api/health", client_host="198.51.100.7")
        assert main_module._get_client_ip(request) == "198.51.100.7"

    def test_get_client_ip_unknown(self):
        request = _make_request("/api/health")
        request.scope["client"] = None
        assert main_module._get_client_ip(request) == "unknown"


class TestCacheControlMiddleware:
    @pytest.mark.asyncio
    async def test_cache_control_for_api_path(self):
        request = _make_request("/api/posts")

        async def call_next(_):
            return Response(status_code=200)

        response = await main_module.add_cache_control_headers(request, call_next)
        assert response.headers["Cache-Control"].startswith("private")
        assert response.headers["Pragma"] == "no-cache"

    @pytest.mark.asyncio
    async def test_cache_control_for_html(self):
        request = _make_request("/index.html")

        async def call_next(_):
            return Response(status_code=200)

        response = await main_module.add_cache_control_headers(request, call_next)
        assert (
            response.headers["Cache-Control"] == "public, max-age=300, must-revalidate"
        )

    @pytest.mark.asyncio
    async def test_cache_control_for_assets(self):
        request = _make_request("/assets/app.js")

        async def call_next(_):
            return Response(status_code=200)

        response = await main_module.add_cache_control_headers(request, call_next)
        assert (
            response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        )

    @pytest.mark.asyncio
    async def test_cache_control_for_css(self):
        request = _make_request("/styles/main.css")

        async def call_next(_):
            return Response(status_code=200)

        response = await main_module.add_cache_control_headers(request, call_next)
        assert (
            response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        )

    @pytest.mark.asyncio
    async def test_cache_control_for_fonts(self):
        request = _make_request("/fonts/ArialUnicodeMS.woff2")

        async def call_next(_):
            return Response(status_code=200)

        response = await main_module.add_cache_control_headers(request, call_next)
        assert (
            response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        )

    @pytest.mark.asyncio
    async def test_cache_control_for_images(self):
        request = _make_request("/images/logo.png")

        async def call_next(_):
            return Response(status_code=200)

        response = await main_module.add_cache_control_headers(request, call_next)
        assert response.headers["Cache-Control"] == "public, max-age=31536000"

    @pytest.mark.asyncio
    async def test_cache_control_for_root_path(self):
        request = _make_request("/")

        async def call_next(_):
            return Response(status_code=200)

        response = await main_module.add_cache_control_headers(request, call_next)
        assert (
            response.headers["Cache-Control"] == "public, max-age=300, must-revalidate"
        )

    @pytest.mark.asyncio
    async def test_cache_control_for_empty_path(self):
        request = _make_request("")

        async def call_next(_):
            return Response(status_code=200)

        response = await main_module.add_cache_control_headers(request, call_next)
        assert (
            response.headers["Cache-Control"] == "public, max-age=300, must-revalidate"
        )


class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_rate_limit_bypass_when_disabled(self):
        request = _make_request("/api/posts")

        async def call_next(_):
            return Response(status_code=200)

        with patch.object(main_module.settings, "rate_limit_enabled", False):
            response = await main_module.add_rate_limit_headers(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_headers_added(self):
        main_module._rate_limit_state.clear()
        request = _make_request("/api/posts", client_host="10.10.10.10")

        async def call_next(_):
            return Response(status_code=200)

        with (
            patch.object(main_module.settings, "rate_limit_enabled", True),
            patch.object(main_module.settings, "rate_limit_window_seconds", 60),
            patch.object(main_module.settings, "rate_limit_requests_per_window", 2),
        ):
            response = await main_module.add_rate_limit_headers(request, call_next)

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "2"
        assert response.headers["X-RateLimit-Window"] == "60"

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_returns_429(self):
        main_module._rate_limit_state.clear()
        client_ip = "10.10.10.11"
        main_module._rate_limit_state[client_ip] = deque([1000.0])
        request = _make_request("/api/posts", client_host=client_ip)

        async def call_next(_):
            return Response(status_code=200)

        with (
            patch.object(main_module.settings, "rate_limit_enabled", True),
            patch.object(main_module.settings, "rate_limit_window_seconds", 60),
            patch.object(main_module.settings, "rate_limit_requests_per_window", 1),
            patch("app.main.time.time", return_value=1001.0),
        ):
            response = await main_module.add_rate_limit_headers(request, call_next)

        assert response.status_code == 429
        assert isinstance(response, JSONResponse)
        assert response.headers["X-RateLimit-Remaining"] == "0"


class TestRootHealth:
    def test_root_returns_health_response(self):
        with patch.object(main_module, "powertools_available", False):
            response = main_module.root()
        assert response.status == "ok"

    def test_health_returns_health_response(self):
        with patch.object(main_module, "powertools_available", False):
            response = main_module.health()
        assert response.status == "ok"
