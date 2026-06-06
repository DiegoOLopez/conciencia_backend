"""
ConciencIA — Entry point del backend FastAPI.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.security import RateLimitMiddleware
from api.v1.router import api_router

settings = get_settings()

# Logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("conciencia")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info("🚀 ConciencIA API iniciando...")
    logger.info(f"   Modelo Gemini: {settings.GEMINI_MODEL}")
    logger.info(f"   OSRM: {settings.OSRM_BASE_URL}")
    yield
    logger.info("🛑 ConciencIA API apagándose...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API de movilidad urbana segura para CDMX. "
        "Sugiere las 3 mejores rutas optimizando tiempo, seguridad y accesibilidad."
    ),
    lifespan=lifespan,
)

# --- Middlewares ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)

# --- Routes ---
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Infraestructura"])
async def health_check():
    """Health check para Railway / monitoreo."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
