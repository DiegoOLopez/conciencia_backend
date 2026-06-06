"""
ConciencIA — Endpoints de rutas.
"""

import logging

from fastapi import APIRouter, HTTPException

from schemas.request import RouteRequest
from schemas.response import RouteResponse
from schemas.pedestrian import PedestrianResponse
from agents.orchestrator import orchestrator
from agents.pedestrian import pedestrian_agent

logger = logging.getLogger(__name__)

router = APIRouter()


from datetime import datetime
import uuid
from schemas.request import RouteRequest, TransportMode
from schemas.response import RouteResponse, RouteOption, Segment, RouteRecommendation

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

        from services.osm_service import osm_service
        from schemas.response import ParadaTransporte

        lat_centro = (request.origin.lat + request.destination.lat) / 2
        lon_centro = (request.origin.lon + request.destination.lon) / 2
        paradas_dicts = await osm_service.get_transit_stops(lat_centro, lon_centro)
        paradas_transporte = [ParadaTransporte(**p) for p in paradas_dicts]

        # Si el usuario seleccionó SÓLO Caminar, usar el Agente Peatonal Especializado
        if len(request.transport_modes) == 1 and request.transport_modes[0] == TransportMode.walk:
            logger.info("Modo exclusivo caminata detectado. Usando pedestrian_agent.")
            import time
            t0 = time.time()
            ped_resp = await pedestrian_agent.calculate_routes(request)
            
            if ped_resp.error:
                raise HTTPException(status_code=400, detail=ped_resp.mensaje)
                
            # Mapear de PedestrianResponse a RouteResponse
            options = []
            for i, p_route in enumerate(ped_resp.rutas):
                segs = [
                    Segment(
                        mode=TransportMode.walk,
                        polyline=[[c.lat, c.lon] for c in p_route.coordenadas_polyline],
                        distance_km=p_route.metricas.distancia_metros / 1000,
                        duration_minutes=p_route.metricas.tiempo_minutos,
                        risk_score=0,
                        description="Caminata de principio a fin"
                    )
                ]
                options.append(RouteOption(
                    rank=i+1,
                    segments=segs,
                    total_time_minutes=p_route.metricas.tiempo_minutos,
                    total_distance_km=p_route.metricas.distancia_metros / 1000,
                    risk_score=0,
                    accessibility_score=p_route.metricas.score_accesibilidad,
                    explanation=p_route.explicacion_ia,
                    summary=p_route.resumen_una_linea,
                    transport_modes_used=[TransportMode.walk],
                    tags=p_route.tags
                ))
            
            recomendacion = None
            if ped_resp.recomendacion:
                recomendacion = RouteRecommendation(
                    ruta_id=ped_resp.recomendacion.ruta_id,
                    score=ped_resp.recomendacion.score,
                    razon=ped_resp.recomendacion.razon
                )
                
            return RouteResponse(
                routes=options,
                recomendacion=recomendacion,
                paradas_transporte=paradas_transporte,
                request_id=str(uuid.uuid4()),
                computed_at=datetime.utcnow(),
                computation_time_ms=(time.time() - t0) * 1000
            )

        # Si hay más modos (metro, bus, etc.), usar el orquestador general
        response = await orchestrator.process_request(request)
        response.paradas_transporte = paradas_transporte

        logger.info(
            f"Respuesta generada: {len(response.routes)} rutas en "
            f"{response.computation_time_ms:.0f}ms con {len(paradas_transporte)} paradas dinámicas"
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


@router.post(
    "/walk",
    response_model=PedestrianResponse,
    summary="Calcular rutas 100% peatonales con OSMnx",
    description="Agente especializado en caminatas. Prioriza FASTEST, SHORTEST, ACCESSIBLE o BALANCED."
)
async def calculate_walk_routes(request: RouteRequest) -> PedestrianResponse:
    """
    Endpoint para el agente de ruteo puramente peatonal.
    """
    logger.info(f"Nuevo request peatonal (OSMnx): {request.origin} -> {request.destination} | {request.priority}")
    response = await pedestrian_agent.calculate_routes(request)
    if response.error:
        # Podríamos arrojar HTTPException, pero el JSON de error es lo que espera el contrato.
        pass
    return response
