"""
ConciencIA — Agente 3: Riesgo.
Evalúa y asigna scores de riesgo a cada segmento y ruta completa.
"""

from agents.base import BaseAgent, AgentContext, AgentResult
from services.cdmx_data_service import cdmx_data_service
from schemas.request import TransportMode


class RiskAgent(BaseAgent):
    """
    Agente de evaluación de riesgo.

    Modelo de scoring heurístico con 7 factores ponderados:
    - Hora nocturna (25%)
    - Incidentes viales cercanos (20%)
    - Número de cruces (15%)
    - Distancia de caminata (15%)
    - Transbordos (10%)
    - Zona conflictiva (10%)
    - Iluminación estimada (5%)
    """

    # Pesos de cada factor de riesgo
    WEIGHTS = {
        "night_hour": 0.25,
        "incidents": 0.20,
        "crossings": 0.15,
        "walk_distance": 0.15,
        "transfers": 0.10,
        "conflict_zone": 0.10,
        "lighting": 0.05,
    }

    def __init__(self):
        super().__init__("risk")

    async def execute(self, context: AgentContext) -> AgentResult:
        candidate_routes = context.get("candidate_routes", [])
        departure_hour = context.get("departure_hour", 12)

        if not candidate_routes:
            return AgentResult(
                success=False, error="No hay rutas candidatas para evaluar"
            )

        scored_routes = []

        for route in candidate_routes:
            # Evaluar cada segmento
            scored_segments = []
            for segment in route.get("segments", []):
                segment_risk = self._evaluate_segment_risk(
                    segment, departure_hour
                )
                scored_segments.append({
                    **segment,
                    "risk_score": segment_risk["total_score"],
                    "risk_factors": segment_risk["factors"],
                })

            # Score de riesgo total de la ruta
            if scored_segments:
                # Promedio ponderado por distancia
                total_dist = sum(s["distance_km"] for s in scored_segments) or 1
                weighted_risk = sum(
                    s["risk_score"] * s["distance_km"] / total_dist
                    for s in scored_segments
                )
            else:
                weighted_risk = 50  # Default

            # Ajustes a nivel de ruta completa
            route_adjustments = self._evaluate_route_level_risk(
                route, departure_hour
            )
            final_risk = min(100, weighted_risk + route_adjustments["adjustment"])

            scored_routes.append({
                **route,
                "segments": scored_segments,
                "risk_score": round(final_risk, 1),
                "risk_breakdown": route_adjustments["breakdown"],
            })

        context.set("scored_routes", scored_routes)

        return AgentResult(
            success=True,
            data={
                "num_routes_scored": len(scored_routes),
                "risk_range": [
                    min(r["risk_score"] for r in scored_routes),
                    max(r["risk_score"] for r in scored_routes),
                ],
            },
        )

    def _evaluate_segment_risk(
        self, segment: dict, hour: int
    ) -> dict:
        """Evalúa el riesgo de un segmento individual."""
        mode = segment.get("mode", TransportMode.WALK.value)
        coords = segment.get("coordinates", [])
        distance_km = segment.get("distance_km", 0)

        factors = {}
        scores = {}

        # --- Factor 1: Hora nocturna ---
        night_score = self._night_risk(hour, mode)
        scores["night_hour"] = night_score
        if night_score > 30:
            factors["night_hour"] = f"Hora {hour}:00 — riesgo nocturno elevado"

        # --- Factor 2: Incidentes viales (zona) ---
        zone_risk = 0
        if coords:
            # Evaluar punto medio del segmento
            mid_idx = len(coords) // 2
            mid_point = coords[mid_idx] if mid_idx < len(coords) else coords[0]
            zone_data = cdmx_data_service.get_risk_for_point(
                mid_point[0], mid_point[1]
            )
            zone_risk = zone_data["risk_level"]
        scores["incidents"] = zone_risk
        if zone_risk > 40:
            factors["incidents"] = f"Zona con incidencia vial: {zone_risk:.0f}/100"

        # --- Factor 3: Cruces (estimación por distancia peatonal) ---
        crossing_score = 0
        if mode == TransportMode.WALK.value:
            # Estimación: ~2 cruces por km en zona urbana
            est_crossings = distance_km * 2
            crossing_score = min(100, est_crossings * 15)
        scores["crossings"] = crossing_score
        if crossing_score > 30:
            factors["crossings"] = f"~{distance_km * 2:.0f} cruces estimados"

        # --- Factor 4: Distancia de caminata ---
        walk_score = 0
        if mode == TransportMode.WALK.value:
            # Más de 1km caminando = riesgo creciente
            if distance_km > 2:
                walk_score = 80
            elif distance_km > 1:
                walk_score = 50
            elif distance_km > 0.5:
                walk_score = 25
            else:
                walk_score = 10
        scores["walk_distance"] = walk_score
        if walk_score > 30:
            factors["walk_distance"] = f"Caminata de {distance_km:.1f} km"

        # --- Factor 5: Zona conflictiva ---
        scores["conflict_zone"] = zone_risk * 0.8  # Correlacionado con incidentes

        # --- Factor 6: Iluminación (proxy por tipo de vía y hora) ---
        lighting_score = 0
        if hour >= 20 or hour < 6:
            if mode == TransportMode.WALK.value:
                lighting_score = 50  # Caminata nocturna
            elif mode in (TransportMode.METRO.value, TransportMode.METROBUS.value):
                lighting_score = 15  # Transporte público iluminado
        scores["lighting"] = lighting_score
        if lighting_score > 30:
            factors["lighting"] = "Baja iluminación estimada"

        # --- Factor 7: Transbordos (se evalúa a nivel de ruta) ---
        scores["transfers"] = 0

        # Calcular score total ponderado
        total_score = sum(
            scores.get(factor, 0) * weight
            for factor, weight in self.WEIGHTS.items()
        )

        return {
            "total_score": round(min(100, total_score), 1),
            "scores": scores,
            "factors": factors,
        }

    def _evaluate_route_level_risk(
        self, route: dict, hour: int
    ) -> dict:
        """Evalúa factores de riesgo a nivel de ruta completa."""
        adjustment = 0
        breakdown = {}

        # Penalización por transbordos
        transfers = route.get("transfers", 0)
        if transfers > 0:
            transfer_penalty = transfers * 5
            adjustment += transfer_penalty
            breakdown["transfers"] = f"+{transfer_penalty} por {transfers} transbordo(s)"

        # Penalización por caminata total alta
        walk_km = route.get("walk_km", 0)
        if walk_km > 1.5 and (hour >= 21 or hour < 6):
            night_walk_penalty = 10
            adjustment += night_walk_penalty
            breakdown["night_walk"] = (
                f"+{night_walk_penalty} por {walk_km:.1f}km de caminata nocturna"
            )

        # Bonificación por usar transporte público (más seguro que caminar)
        modes = route.get("modes", [])
        if TransportMode.METRO.value in modes or TransportMode.METROBUS.value in modes:
            transit_bonus = -5
            adjustment += transit_bonus
            breakdown["transit_bonus"] = f"{transit_bonus} por usar transporte público"

        return {"adjustment": adjustment, "breakdown": breakdown}

    @staticmethod
    def _night_risk(hour: int, mode: str) -> float:
        """Score de riesgo por hora nocturna según modo de transporte."""
        is_walking = mode == TransportMode.WALK.value

        if 6 <= hour < 18:
            return 5 if is_walking else 0
        elif 18 <= hour < 20:
            return 20 if is_walking else 10
        elif 20 <= hour < 22:
            return 45 if is_walking else 20
        elif 22 <= hour or hour < 1:
            return 75 if is_walking else 35
        else:  # 1-6
            return 90 if is_walking else 45
