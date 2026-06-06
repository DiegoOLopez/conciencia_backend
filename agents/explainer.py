"""
ConciencIA — Agente 5: Explicador.
Traduce datos numéricos a explicaciones en lenguaje natural.
"""

from agents.base import BaseAgent, AgentContext, AgentResult
from services.gemini_service import gemini_service


class ExplainerAgent(BaseAgent):
    """
    Agente explicador.

    Responsabilidades:
    - Recibir las 3 rutas optimizadas con scores
    - Generar explicaciones en lenguaje natural (español)
    - Usar Gemini para explicaciones ricas, con fallback a templates
    - Generar tags descriptivos para cada ruta
    """

    def __init__(self):
        super().__init__("explainer")

    async def execute(self, context: AgentContext) -> AgentResult:
        top_routes = context.get("top_routes", [])
        request = context.get("request")
        departure_hour = context.get("departure_hour", 12)

        if not top_routes:
            return AgentResult(
                success=False, error="No hay rutas para explicar"
            )

        priority = request.priority.value if request else "BALANCED"

        # Preparar datos para Gemini
        routes_data = []
        for route in top_routes:
            routes_data.append({
                "total_time_minutes": route.get("total_time_minutes", 0),
                "total_distance_km": route.get("total_distance_km", 0),
                "risk_score": route.get("risk_score", 0),
                "accessibility_score": route.get("accessibility_score", 50),
                "transport_modes": route.get("modes", []),
                "walk_km": route.get("walk_km", 0),
                "transfers": route.get("transfers", 0),
                "type": route.get("type", "unknown"),
            })

        # Generar explicaciones
        explanations = await gemini_service.generate_explanations(
            routes_data, priority, departure_hour
        )

        # Asignar explicaciones a las rutas
        explained_routes = []
        for i, route in enumerate(top_routes):
            explanation_data = (
                explanations[i] if i < len(explanations) else {}
            )

            explained_routes.append({
                **route,
                "explanation": explanation_data.get(
                    "explanation",
                    self._default_explanation(route, i),
                ),
                "summary": explanation_data.get(
                    "summary",
                    self._default_summary(route),
                ),
                "tags": explanation_data.get(
                    "tags",
                    self._generate_tags(route),
                ),
            })

        context.set("explained_routes", explained_routes)

        return AgentResult(
            success=True,
            data={
                "num_explained": len(explained_routes),
                "used_gemini": bool(gemini_service._client),
            },
        )

    @staticmethod
    def _default_explanation(route: dict, index: int) -> str:
        """Explicación por defecto cuando Gemini no está disponible."""
        time_min = route.get("total_time_minutes", 0)
        risk = route.get("risk_score", 0)
        modes = ", ".join(route.get("modes", ["caminata"]))
        walk = route.get("walk_km", 0)

        if index == 0:
            return (
                f"Ruta recomendada: {time_min:.0f} minutos usando {modes}. "
                f"Nivel de riesgo: {risk:.0f}/100. "
                f"Caminata total: {walk:.1f} km."
            )
        elif risk < 30:
            return (
                f"Opción segura: riesgo de solo {risk:.0f}/100 en {time_min:.0f} minutos. "
                f"Usa {modes} con {walk:.1f} km de caminata."
            )
        else:
            return (
                f"Alternativa de {time_min:.0f} minutos usando {modes}. "
                f"Riesgo: {risk:.0f}/100, caminata: {walk:.1f} km."
            )

    @staticmethod
    def _default_summary(route: dict) -> str:
        """Resumen por defecto de una línea."""
        rtype = route.get("type", "")
        time_min = route.get("total_time_minutes", 0)

        if rtype == "transit":
            return f"Transporte público — {time_min:.0f} min"
        elif rtype == "walking":
            return f"Caminando — {time_min:.0f} min"
        elif rtype == "driving":
            return f"En auto — {time_min:.0f} min"
        else:
            return f"Ruta mixta — {time_min:.0f} min"

    @staticmethod
    def _generate_tags(route: dict) -> list[str]:
        """Genera tags descriptivos para una ruta."""
        tags = []
        risk = route.get("risk_score", 50)
        walk_km = route.get("walk_km", 0)
        transfers = route.get("transfers", 0)
        rtype = route.get("type", "")

        if risk < 25:
            tags.append("Muy segura")
        elif risk < 40:
            tags.append("Segura")

        if walk_km < 0.3:
            tags.append("Mínima caminata")
        elif walk_km < 0.8:
            tags.append("Poca caminata")
        elif walk_km > 1.5:
            tags.append("Mucha caminata")

        if transfers == 0 and rtype == "transit":
            tags.append("Sin transbordo")
        elif transfers > 1:
            tags.append("Varios transbordos")

        if rtype == "transit":
            tags.append("Transporte público")
        elif rtype == "walking":
            tags.append("Solo caminata")

        return tags[:3]

    async def fallback(self, context: AgentContext, error: Exception) -> AgentResult:
        """Fallback: usar explicaciones template para todas las rutas."""
        top_routes = context.get("top_routes", [])
        explained_routes = []

        for i, route in enumerate(top_routes):
            explained_routes.append({
                **route,
                "explanation": self._default_explanation(route, i),
                "summary": self._default_summary(route),
                "tags": self._generate_tags(route),
            })

        context.set("explained_routes", explained_routes)

        return AgentResult(
            success=True,
            data={"num_explained": len(explained_routes), "used_gemini": False},
        )
