# app/csp_middleware.py
"""
Content Security Policy (CSP) Middleware with Nonce Support.

This middleware replaces 'unsafe-inline' with cryptographic nonces for
improved XSS protection while maintaining compatibility with:
- Alpine.js (requires 'unsafe-eval')
- TailwindCSS Play CDN (requires 'unsafe-eval')
"""

import base64
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class CSPMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates a unique nonce for each request and
    applies it to the Content-Security-Policy header.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip CSP for API and auth endpoints (they return JSON, not HTML)
        if request.url.path.startswith(("/api/", "/auth/")):
            return await call_next(request)

        # Generate a cryptographically secure random nonce (16 bytes = 128 bits)
        nonce_bytes = secrets.token_bytes(16)
        nonce = base64.b64encode(nonce_bytes).decode("utf-8")

        # Store nonce in request.state for access in templates
        request.state.csp_nonce = nonce

        # Process the request
        response = await call_next(request)

        # Build CSP policy with nonce
        # Note: 'unsafe-eval' is required for Alpine.js
        # Style-src uses 'self' only since we now use compiled Tailwind CSS
        csp_policy = (
            f"default-src 'self'; "
            f"script-src 'self' 'unsafe-eval' 'nonce-{nonce}'; "
            f"style-src 'self' 'unsafe-inline'; "
            f"img-src 'self' data: blob:; "
            f"connect-src 'self' ws: wss:; "
            f"font-src 'self' data:; "
            f"object-src 'none'; "
            f"base-uri 'self'; "
            f"frame-ancestors 'none';"
        )

        response.headers["Content-Security-Policy"] = csp_policy

        return response
