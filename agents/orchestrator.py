"""
ConciencIA — Agente 1: Orquestador.
Coordina el flujo completo entre todos los agentes.
"""

import time
import uuid
from datetime import datetime, timezone

from agents.base import BaseAgent, AgentContext, AgentResult
from agents.privacy import PrivacyAgent
from agents.urban_data import UrbanDataAgent
from agents.risk import RiskAgent
from agents.optimizer import OptimizerAgent
from agents.explainer import ExplainerAgent
from schemas.request import RouteRequest, TransportMode
from schemas.response import (
    RouteResponse,
    RouteOption,
    Segment,
)


class OrchestratorAgent(BaseAgent):
    """
    Agente orquestador.

    Pipeline secuencial:
    1. Privacidad → valida y sanitiza el request
    2. Datos Urbanos → recopila rutas candidatas y datos de CDMX
    3. Riesgo → asigna scores de riesgo a cada segmento
    4. Optimizador → selecciona las 3 mejores rutas
    5. Explicador → genera explicaciones en lenguaje natural

    No usa LLM directamente. Es lógica determinista de orquestación.
    """

    def __init__(self):
        super().__init__("orchestrator")
        self.privacy_agent = PrivacyAgent()
        self.urban_data_agent = UrbanDataAgent()
        self.risk_agent = RiskAgent()
        self.optimizer_agent = OptimizerAgent()
        self.explainer_agent = ExplainerAgent()

    async def execute(self, context: AgentContext) -> AgentResult:
        """Ejecuta el pipeline completo de agentes."""
        pipeline_start = time.time()

        # ======================================================================
        # Paso 1: Agente de Privacidad
        # ======================================================================
        self.logger.info(f"[{context.request_id}] Paso 1/5: Privacidad")
        privacy_result = await self.privacy_agent.run(context)

        if not privacy_result.success:
            return AgentResult(
                success=False,
                error=f"Validación de privacidad fallida: {privacy_result.error}",
            )

        # ======================================================================
        # Paso 2: Agente de Datos Urbanos
        # ======================================================================
        self.logger.info(f"[{context.request_id}] Paso 2/5: Datos Urbanos")
        urban_result = await self.urban_data_agent.run(context)

        if not urban_result.success:
            return AgentResult(
                success=False,
                error=f"Obtención de datos urbanos fallida: {urban_result.error}",
            )

        # ======================================================================
        # Paso 3: Agente de Riesgo
        # ======================================================================
        self.logger.info(f"[{context.request_id}] Paso 3/5: Evaluación de Riesgo")
        risk_result = await self.risk_agent.run(context)

        if not risk_result.success:
            self.logger.warning(
                f"Agente de riesgo falló, continuando con scores default: "
                f"{risk_result.error}"
            )
            # Continuar con scores de riesgo default
            scored_routes = context.get("candidate_routes", [])
            for route in scored_routes:
                route["risk_score"] = 50  # Default
                for seg in route.get("segments", []):
                    seg["risk_score"] = 50
            context.set("scored_routes", scored_routes)

        # ======================================================================
        # Paso 4: Agente Optimizador
        # ======================================================================
        self.logger.info(f"[{context.request_id}] Paso 4/5: Optimización")
        optimizer_result = await self.optimizer_agent.run(context)

        if not optimizer_result.success:
            return AgentResult(
                success=False,
                error=f"Optimización fallida: {optimizer_result.error}",
            )

        # ======================================================================
        # Paso 5: Agente Explicador
        # ======================================================================
        self.logger.info(f"[{context.request_id}] Paso 5/5: Generación de Explicaciones")
        explainer_result = await self.explainer_agent.run(context)

        if not explainer_result.success:
            self.logger.warning(
                f"Agente explicador falló, usando explicaciones default: "
                f"{explainer_result.error}"
            )

        # ======================================================================
        # Ensamblar respuesta final
        # ======================================================================
        pipeline_elapsed = (time.time() - pipeline_start) * 1000
        response = self._build_response(context, pipeline_elapsed)

        self.logger.info(
            f"[{context.request_id}] Pipeline completado en {pipeline_elapsed:.0f}ms. "
            f"Rutas generadas: {len(response.routes)}"
        )

        return AgentResult(
            success=True,
            data={"response": response},
            execution_time_ms=pipeline_elapsed,
        )

    def _build_response(
        self, context: AgentContext, computation_time_ms: float
    ) -> RouteResponse:
        """Ensambla la respuesta final del pipeline."""
        explained_routes = context.get("explained_routes", [])
        top_routes = context.get("top_routes", [])

        # Usar explained_routes si disponibles, sino top_routes
        routes_to_use = explained_routes if explained_routes else top_routes

        route_options = []
        for route in routes_to_use[:3]:
            segments = []
            for seg in route.get("segments", []):
                segments.append(Segment(
                    mode=TransportMode(seg["mode"]),
                    polyline=seg.get("coordinates", []),
                    distance_km=seg.get("distance_km", 0),
                    duration_minutes=seg.get("duration_minutes", 0),
                    risk_score=seg.get("risk_score", 50),
                    description=seg.get("description", ""),
                    transit_line=seg.get("transit_line"),
                    transit_stops=seg.get("transit_stops"),
                ))

            modes_used = list({
                TransportMode(s.mode) for s in segments
            })

            route_options.append(RouteOption(
                rank=route.get("rank", len(route_options) + 1),
                segments=segments,
                total_time_minutes=route.get("total_time_minutes", 0),
                total_distance_km=route.get("total_distance_km", 0),
                risk_score=route.get("risk_score", 50),
                accessibility_score=route.get("accessibility_score", 50),
                explanation=route.get(
                    "explanation",
                    "Ruta calculada automáticamente."
                ),
                summary=route.get("summary", "Ruta disponible"),
                transport_modes_used=modes_used,
                tags=route.get("tags", []),
            ))

        return RouteResponse(
            routes=route_options,
            request_id=context.request_id,
            computed_at=datetime.now(timezone.utc),
            computation_time_ms=round(computation_time_ms, 1),
        )

    async def process_request(self, request: RouteRequest) -> RouteResponse:
        """
        Entry point público para procesar un RouteRequest.
        Crea el contexto y ejecuta el pipeline completo.
        """
        request_id = str(uuid.uuid4())
        context = AgentContext(request_id=request_id)
        context.set("request", request)

        result = await self.run(context)

        if not result.success:
            raise RuntimeError(
                f"Pipeline fallido: {result.error}\n"
                f"Errores: {context.errors}"
            )

        return result.data["response"]


# Singleton
orchestrator = OrchestratorAgent()
