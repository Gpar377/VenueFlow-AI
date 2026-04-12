"""
VenueFlow AI — Security Middleware
Rate limiting, input sanitization, CSP headers, and CORS.
"""
import time
import re
import html
from collections import defaultdict
from typing import Dict

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """Simple in-memory rate limiter per IP address."""

    def __init__(self):
        self._requests: Dict[str, list] = defaultdict(list)
        self._limits = {
            "/api/chat": (10, 60),     # 10 requests per 60 seconds
            "default": (60, 60),       # 60 requests per 60 seconds
        }

    def is_allowed(self, ip: str, path: str) -> bool:
        """Check if the request is within rate limits."""
        now = time.time()
        key = f"{ip}:{path}"

        # Get limit for this path
        max_requests, window = self._limits.get(path, self._limits["default"])

        # Clean old entries
        self._requests[key] = [t for t in self._requests[key] if now - t < window]

        if len(self._requests[key]) >= max_requests:
            return False

        self._requests[key].append(now)
        return True

    def get_remaining(self, ip: str, path: str) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        key = f"{ip}:{path}"
        max_requests, window = self._limits.get(path, self._limits["default"])
        active = [t for t in self._requests[key] if now - t < window]
        return max(0, max_requests - len(active))


# Global rate limiter instance
rate_limiter = RateLimiter()


class SecurityMiddleware(BaseHTTPMiddleware):
    """Adds security headers and rate limiting to all responses."""

    async def dispatch(self, request: Request, call_next):
        # ── Rate limiting ─────────────────────────────────────
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        if path.startswith("/api/"):
            if not rate_limiter.is_allowed(client_ip, path):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please slow down.",
                )

        # ── Process request ───────────────────────────────────
        response = await call_next(request)

        # ── Security headers ──────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "microphone=(self), camera=()"

        # CSP — allow inline styles/scripts for our SPA + Google Fonts
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://maps.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https://*.googleapis.com https://*.gstatic.com; "
            "connect-src 'self' ws: wss:; "
        )
        response.headers["Content-Security-Policy"] = csp

        return response


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.
    - Strip HTML tags
    - Escape remaining HTML entities
    - Limit length
    - Remove control characters
    """
    if not text:
        return ""

    # Truncate
    text = text[:max_length]

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Escape HTML entities
    text = html.escape(text, quote=True)

    # Remove control characters (except newline, tab)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return text.strip()
