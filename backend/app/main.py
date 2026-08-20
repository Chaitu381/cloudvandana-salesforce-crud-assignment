from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.objects import router as objects_router
from app.core.config import get_settings
from app.core.middleware import OriginProtectionMiddleware, SecurityHeadersMiddleware

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.origin_allowlist),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
app.add_middleware(OriginProtectionMiddleware, allowed_origins=settings.origin_allowlist)
app.add_middleware(SecurityHeadersMiddleware, production=settings.environment.lower() == "production")

app.include_router(auth_router)
app.include_router(objects_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "salesforceConfigured": settings.is_salesforce_configured}


# Resolve the compiled frontend in both supported layouts:
# - Docker runtime: /app/static
# - Local source build: <project>/frontend/dist
_static_candidates = (
    Path(__file__).resolve().parents[1] / "static",
    Path(__file__).resolve().parents[2] / "frontend" / "dist",
)
static_dir = next((path for path in _static_candidates if (path / "index.html").is_file()), None)

if static_dir is not None:
    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        requested = static_dir / full_path
        if full_path and requested.is_file():
            return FileResponse(requested)
        return FileResponse(static_dir / "index.html")
