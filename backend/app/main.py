from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS — allow the local Next.js dev server and any origin in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}

# Flatten /payments/* routes to root (no API versioning prefix for simplicity)
from app.api.endpoints.payments import router as payments_router
app.include_router(payments_router, prefix="/payments", tags=["Payments"])

from app.api.api import api_router
# API router (versioned)
app.include_router(api_router, prefix=settings.API_V1_STR)
