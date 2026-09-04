import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.observability.logging_config import configure_logging
from app.middleware.request_id import RequestIDMiddleware, REQUEST_ID_HEADER
from app.middleware.logging import StructuredLoggingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.security.rate_limit import limiter
from app.schemas.errors import ErrorResponse
from app.security.auth import get_current_user

# Initialize structured logging
configure_logging(level="DEBUG" if settings.ENVIRONMENT == "development" else "INFO")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pass Redis URI to limiter dynamically on startup if available
    limiter._storage_uri = settings.REDIS_URL
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost runs first) ─────────────────────────

app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiter ──────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Global Exception Handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None)
    
    if settings.ENVIRONMENT == "development":
        message = str(exc)
    else:
        message = "Internal server error"
        
    err = ErrorResponse.build(error="internal_error", message=message, request_id=req_id)
    return JSONResponse(status_code=500, content=err.model_dump())


# ── Core Endpoints ────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Check DB connectivity and return 503 if unavailable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})


@app.get("/metrics", tags=["Observability"], dependencies=[Depends(get_current_user)])
async def metrics():
    """Prometheus metrics endpoint. Internal only (requires API Key)."""
    from fastapi.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ── Routers ───────────────────────────────────────────────────────────────────

from app.api.endpoints.payments import router as payments_router
app.include_router(payments_router, prefix="/payments", tags=["Payments"])

from app.api.api import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)

from app.webhooks.router import router as webhooks_router
app.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
