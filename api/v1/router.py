"""
ConciencIA — Router principal de la API v1.
"""

from fastapi import APIRouter

from api.v1.routes import router as routes_router

api_router = APIRouter()

api_router.include_router(
    routes_router,
    prefix="/routes",
    tags=["Rutas"],
)
