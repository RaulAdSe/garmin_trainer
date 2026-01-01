"""Security headers middleware for FastAPI."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff - Prevents MIME type sniffing
    - X-Frame-Options: DENY - Prevents clickjacking attacks
    - Strict-Transport-Security: max-age=31536000; includeSubDomains - Enforces HTTPS
    - Content-Security-Policy: Configurable CSP rules
    - Referrer-Policy: strict-origin-when-cross-origin - Controls referrer information
    - Permissions-Policy: Restricts browser features
    """

    def __init__(
        self,
        app,
        content_security_policy: str | None = None,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
    ):
        """Initialize security headers middleware.

        Args:
            app: The ASGI application.
            content_security_policy: Custom CSP policy. If None, uses a restrictive default.
            enable_hsts: Whether to add HSTS header (disable for local development).
            hsts_max_age: HSTS max-age in seconds (default: 1 year).
            hsts_include_subdomains: Include subdomains in HSTS.
            hsts_preload: Add preload directive to HSTS.
        """
        super().__init__(app)
        self.content_security_policy = content_security_policy or self._default_csp()
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload

    def _default_csp(self) -> str:
        """Return a restrictive default Content Security Policy.

        This is suitable for an API that doesn't serve HTML content.
        For APIs, we want to be very restrictive since we're only serving JSON.
        """
        return "; ".join([
            "default-src 'none'",  # Deny everything by default
            "frame-ancestors 'none'",  # Prevent embedding in frames (complements X-Frame-Options)
        ])

    def _build_hsts_header(self) -> str:
        """Build the HSTS header value."""
        parts = [f"max-age={self.hsts_max_age}"]
        if self.hsts_include_subdomains:
            parts.append("includeSubDomains")
        if self.hsts_preload:
            parts.append("preload")
        return "; ".join(parts)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to the response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.content_security_policy

        # HSTS - only add if enabled (should be disabled for local dev without HTTPS)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = self._build_hsts_header()

        # Additional security headers
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature-Policy)
        # Disable various browser features that an API doesn't need
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        return response
