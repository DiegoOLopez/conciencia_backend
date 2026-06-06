"""
ConciencIA — Middleware de seguridad.
Rate limiting básico, validación de coordenadas, sanitización.
"""

import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiter simple basado en IP (en memoria, adecuado para MVP)."""

    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Limpiar timestamps antiguos
        self._requests[client_ip] = [
            ts for ts in self._requests[client_ip]
            if now - ts < self.window_seconds
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit excedido para IP: {client_ip}")
            raise HTTPException(
                status_code=429,
                detail="Demasiadas solicitudes. Intenta de nuevo en un minuto.",
            )

        self._requests[client_ip].append(now)
        response = await call_next(request)
        return response


def validate_cdmx_coordinates(lat: float, lon: float) -> bool:
    """Valida que las coordenadas estén dentro de los límites de CDMX."""
    return (
        settings.CDMX_LAT_MIN <= lat <= settings.CDMX_LAT_MAX
        and settings.CDMX_LON_MIN <= lon <= settings.CDMX_LON_MAX
    )


def truncate_coordinate(value: float, decimals: int = 4) -> float:
    """
    Trunca coordenada a N decimales para minimización de datos.
    4 decimales ≈ 11m de precisión — suficiente para routing urbano.
    """
    factor = 10 ** decimals
    return int(value * factor) / factor
