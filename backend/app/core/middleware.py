from __future__ import annotations

from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class OriginProtectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_origins: set[str]):
        super().__init__(app)
        self.allowed_origins = {origin.rstrip("/") for origin in allowed_origins}

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method.upper() in {"POST", "PATCH", "PUT", "DELETE"}:
            origin = request.headers.get("origin")
            if origin:
                if origin.rstrip("/") not in self.allowed_origins:
                    return JSONResponse({"detail": "Origin is not allowed"}, status_code=403)
            else:
                referer = request.headers.get("referer")
                if referer:
                    parsed = urlparse(referer)
                    ref_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
                    if ref_origin not in self.allowed_origins:
                        return JSONResponse({"detail": "Origin is not allowed"}, status_code=403)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, production: bool):
        super().__init__(app)
        self.production = production

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if self.production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
