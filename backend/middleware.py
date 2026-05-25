"""Security middleware: rate limiting, body size limits, security headers."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import config

logger = logging.getLogger(__name__)

# In-memory rate limiting store: { "endpoint:ip:window": count }
_rate_store: dict[str, int] = {}
_rate_reset: float = time.time() + 60.0  # reset every minute


def _rate_limit_key(key: str, limit: int) -> None:
    """Check and enforce rate limit for a given key."""
    global _rate_reset, _rate_store

    now = time.time()
    if now > _rate_reset:
        _rate_store.clear()
        _rate_reset = now + 60.0

    current = _rate_store.get(key, 0)
    if current >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )
    _rate_store[key] = current + 1


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with per-endpoint and per-IP tracking."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not config.rate_limit_enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Auth endpoints have stricter limits
        if path.startswith("/api/auth"):
            limit = config.rate_limit_auth_per_minute
        elif path.startswith("/api/enterprise"):
            limit = config.rate_limit_enterprise_per_minute
        else:
            limit = config.rate_limit_api_per_minute

        key = f"{path}:{client_ip}"
        try:
            _rate_limit_key(key, limit)
        except HTTPException:
            logger.warning("Rate limit exceeded: path=%s ip=%s", path, client_ip)
            raise

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security-related headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=()"
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to every response for tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforce maximum request body size."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        max_bytes = config.max_body_size_mb * 1024 * 1024
        if content_length and int(content_length) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"请求体大小超过限制 ({config.max_body_size_mb}MB)",
            )
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests with timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        response = await call_next(request)
        elapsed_ms = (time.time() - start) * 1000
        # Skip logging for static files
        if not request.url.path.startswith("/assets"):
            logger.info(
                "%s %s -> %s (%.1fms)",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        return response
