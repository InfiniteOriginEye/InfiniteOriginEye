"""
Swarm Command & Control — Backend Application
Entry point: uvicorn app.main:app
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    setup_logging()
    # TODO: Connect to PostgreSQL, Redis, Kafka on startup
    yield
    # TODO: Gracefully close connections on shutdown


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Swarm Command & Control — India Disaster Rescue Drone Swarm System",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — allow dashboards in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": settings.APP_NAME}


# ── API v1 routes ────────────────────────────────────────────
# TODO: Include routers as they are built:
# from app.api.v1.endpoints import incidents, drones, rescue, advisories
# app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["incidents"])
# app.include_router(drones.router, prefix="/api/v1/drones", tags=["drones"])
# app.include_router(rescue.router, prefix="/api/v1/rescue", tags=["rescue"])
# app.include_router(advisories.router, prefix="/api/v1/advisories", tags=["advisories"])
