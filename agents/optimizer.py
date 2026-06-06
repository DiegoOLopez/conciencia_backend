"""
ConciencIA — Agente 4: Optimizador de Ruta.
Selecciona las 3 mejores rutas según la prioridad del usuario.
"""

from agents.base import BaseAgent, AgentContext, AgentResult
from schemas.request import TravelPriority, TransportMode


class OptimizerAgent(BaseAgent):
    """
    Agente optimizador de rutas.

    Responsabilidades:
    - Evaluar rutas candidatas con scores multi-dimensionales
    - Calcular score de accesibilidad
    - Seleccionar top 3 según prioridad del usuario (SPEED, SAFETY, BALANCED)
    - Garantizar diversidad en las opciones presentadas
    """

    def __init__(self):
        super().__init__("optimizer")

    async def execute(self, context: AgentContext) -> AgentResult:
        scored_routes = context.get("scored_routes", [])
        request = context.get("request")

        if not scored_routes:
            context.set("top_routes", [])
            return AgentResult(
                success=True, 
                data={"num_optimized": 0, "scores": []}
            )

        priority = request.priority if request else TravelPriority.BALANCED

        # 1. Calcular scores compuestos para cada ruta
        evaluated_routes = []
        for route in scored_routes:
            accessibility = self._calculate_accessibility(route)
            composite = self._calculate_composite_score(route, priority)

            evaluated_routes.append({
                **route,
                "accessibility_score": accessibility,
                "composite_score": composite,
            })

        # 2. Ordenar por composite score (mayor = mejor)
        evaluated_routes.sort(key=lambda r: r["composite_score"], reverse=True)

        # 3. Seleccionar top 3 con diversidad
        top_routes = self._select_diverse_top3(evaluated_routes, priority)

        # 4. Asignar ranks
        for i, route in enumerate(top_routes):
            route["rank"] = i + 1

        context.set("top_routes", top_routes)

        return AgentResult(
            success=True,
            data={
                "num_optimized": len(top_routes),
                "scores": [
                    {
                        "rank": r["rank"],
                        "type": r.get("type"),
                        "time": r["total_time_minutes"],
                        "risk": r["risk_score"],
                        "composite": r["composite_score"],
                    }
                    for r in top_routes
                ],
            },
        )

    def _calculate_composite_score(
        self, route: dict, priority: TravelPriority
    ) -> float:
        """
        Calcula score compuesto (0-100, mayor = mejor ruta).
        Los pesos varían según la prioridad del usuario.
        """
        time_min = route.get("total_time_minutes", 60)
        risk = route.get("risk_score", 50)
        walk_km = route.get("walk_km", 0)
        transfers = route.get("transfers", 0)

        # Normalizar tiempo (0-100 donde 100 = más rápido)
        # Asumimos rango 5-120 minutos para CDMX
        time_score = max(0, 100 - ((time_min - 5) / 115) * 100)

        # Invertir riesgo (0-100 donde 100 = más seguro)
        safety_score = 100 - risk

        # Score de comodidad (menos caminata y transbordos = mejor)
        comfort_score = max(0, 100 - (walk_km * 20) - (transfers * 15))

        # Pesos según prioridad
        weights = {
            TravelPriority.SPEED: {
                "time": 0.60, "safety": 0.25, "comfort": 0.15
            },
            TravelPriority.SAFETY: {
                "time": 0.15, "safety": 0.60, "comfort": 0.25
            },
            TravelPriority.BALANCED: {
                "time": 0.35, "safety": 0.40, "comfort": 0.25
            },
        }

        w = weights.get(priority, weights[TravelPriority.BALANCED])
        composite = (
            time_score * w["time"]
            + safety_score * w["safety"]
            + comfort_score * w["comfort"]
        )

        return round(composite, 2)

    @staticmethod
    def _calculate_accessibility(route: dict) -> float:
        """
        Calcula score de accesibilidad (0-100).
        Evalúa la facilidad de uso para personas con movilidad reducida.
        """
        score = 100.0
        modes = route.get("modes", [])
        walk_km = route.get("walk_km", 0)
        transfers = route.get("transfers", 0)

        # Penalización por caminata larga
        if walk_km > 2:
            score -= 30
        elif walk_km > 1:
            score -= 15
        elif walk_km > 0.5:
            score -= 5

        # Penalización por transbordos
        score -= transfers * 10

        # Bonificación por usar Metro (accesible en muchas estaciones)
        if TransportMode.METRO.value in modes:
            score += 5

        # Penalización por usar sólo caminata larga
        if modes == [TransportMode.WALK.value] and walk_km > 1.5:
            score -= 15

        return round(max(0, min(100, score)), 1)

    def _select_diverse_top3(
        self, routes: list[dict], priority: TravelPriority
    ) -> list[dict]:
        """
        Selecciona 3 rutas asegurando diversidad de tipos.
        Evita devolver 3 rutas del mismo tipo.
        """
        if len(routes) <= 3:
            return routes

        selected = [routes[0]]  # La mejor siempre entra
        used_types = {routes[0].get("type")}

        # Intentar agregar rutas de tipos distintos
        for route in routes[1:]:
            if len(selected) >= 3:
                break
            route_type = route.get("type")
            if route_type not in used_types:
                selected.append(route)
                used_types.add(route_type)

        # Si aún faltan, llenar con las mejores restantes
        for route in routes[1:]:
            if len(selected) >= 3:
                break
            if route not in selected:
                selected.append(route)

        # Re-ordenar por composite score
        selected.sort(key=lambda r: r["composite_score"], reverse=True)

        return selected[:3]
