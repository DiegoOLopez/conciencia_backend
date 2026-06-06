"""
ConciencIA — Endpoints de rutas.
"""

import logging

from fastapi import APIRouter, HTTPException

from schemas.request import RouteRequest
from schemas.response import RouteResponse
from agents.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=RouteResponse,
    summary="Calcular rutas óptimas",
    description=(
        "Recibe origen, destino, hora de salida, modos de transporte y prioridad. "
        "Devuelve las 3 mejores rutas con scores de riesgo, accesibilidad, "
        "y explicaciones en lenguaje natural."
    ),
    responses={
        200: {"description": "3 rutas optimizadas"},
        400: {"description": "Request inválido (coordenadas fuera de CDMX, etc.)"},
        500: {"description": "Error interno del pipeline de agentes"},
    },
)
async def calculate_routes(request: RouteRequest) -> RouteResponse:
    """
    Endpoint principal: calcula las 3 mejores rutas.

    Internamente ejecuta el pipeline de 6 agentes:
    Privacidad → Datos Urbanos → Riesgo → Optimizador → Explicador
    """
    try:
        logger.info(
            f"Nuevo request: {request.origin.lat},{request.origin.lon} → "
            f"{request.destination.lat},{request.destination.lon} "
            f"| Prioridad: {request.priority.value} "
            f"| Modos: {[m.value for m in request.transport_modes]}"
        )

        response = await orchestrator.process_request(request)

        logger.info(
            f"Respuesta generada: {len(response.routes)} rutas en "
            f"{response.computation_time_ms:.0f}ms"
        )

        return response

    except RuntimeError as e:
        logger.error(f"Pipeline fallido: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno al calcular rutas. Intenta de nuevo.",
        )
