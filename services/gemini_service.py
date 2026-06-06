"""
ConciencIA — Servicio de Google Gemini.
Wrapper async para generación de texto con Gemini.
"""

import json
import logging
import time

import google.generativeai as genai

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiService:
    """Wrapper sobre Google Generative AI para el Agente Explicador."""

    def __init__(self):
        self._configured = False
        self._model = None

    def _ensure_configured(self):
        """Configura Gemini al primer uso (lazy init)."""
        if not self._configured:
            if not settings.GEMINI_API_KEY:
                logger.warning(
                    "GEMINI_API_KEY no configurada. "
                    "El Agente Explicador usará respuestas template."
                )
                return
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(settings.GEMINI_MODEL)
            self._configured = True
            logger.info(f"Gemini configurado con modelo: {settings.GEMINI_MODEL}")

    async def generate_explanations(
        self,
        routes_data: list[dict],
        priority: str,
        departure_hour: int,
    ) -> list[dict]:
        """
        Genera explicaciones en lenguaje natural para las rutas.

        Args:
            routes_data: Lista de dicts con datos de cada ruta (tiempo, riesgo, etc.)
            priority: Prioridad del usuario (SPEED, SAFETY, BALANCED)
            departure_hour: Hora de salida (0-23)

        Returns:
            Lista de dicts con 'explanation' y 'summary' por ruta.
        """
        self._ensure_configured()

        if not self._model:
            return self._generate_template_explanations(routes_data, priority)

        prompt = self._build_prompt(routes_data, priority, departure_hour)

        try:
            start_time = time.time()
            response = self._model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.7,
                    max_output_tokens=1024,
                ),
            )
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"Gemini respondió en {elapsed_ms:.0f}ms")

            # Parsear respuesta JSON
            result = json.loads(response.text)

            if isinstance(result, list) and len(result) >= len(routes_data):
                return result[:len(routes_data)]
            elif isinstance(result, dict) and "routes" in result:
                return result["routes"][:len(routes_data)]
            else:
                logger.warning("Respuesta de Gemini con formato inesperado, usando template")
                return self._generate_template_explanations(routes_data, priority)

        except Exception as e:
            logger.error(f"Error al generar explicaciones con Gemini: {e}")
            return self._generate_template_explanations(routes_data, priority)

    def _build_prompt(
        self,
        routes_data: list[dict],
        priority: str,
        departure_hour: int,
    ) -> str:
        """Construye el prompt para Gemini."""
        time_context = "de noche" if departure_hour >= 22 or departure_hour < 6 else "de día"

        routes_text = ""
        for i, route in enumerate(routes_data, 1):
            routes_text += (
                f"\nRuta {i}:\n"
                f"  - Tiempo total: {route.get('total_time_minutes', 0):.0f} minutos\n"
                f"  - Distancia: {route.get('total_distance_km', 0):.1f} km\n"
                f"  - Score de riesgo: {route.get('risk_score', 0):.0f}/100 "
                f"(0=seguro, 100=peligroso)\n"
                f"  - Modos: {', '.join(route.get('transport_modes', []))}\n"
                f"  - Caminata total: {route.get('walk_km', 0):.1f} km\n"
                f"  - Transbordos: {route.get('transfers', 0)}\n"
            )

        return f"""Eres un asistente de movilidad urbana en la Ciudad de México.
El usuario viaja {time_context} (hora: {departure_hour}:00) y su prioridad es: {priority}.

Estas son las 3 rutas calculadas:
{routes_text}

Genera una respuesta JSON con una lista de objetos. Cada objeto debe tener:
- "explanation": string con 2-3 oraciones comparando la ruta con las demás. 
  Menciona trade-offs concretos de tiempo vs seguridad. Habla en español, 
  tono amigable y conciso.
- "summary": string de máximo 8 palabras resumiendo la ruta.
- "tags": lista de 1-3 etiquetas descriptivas cortas en español 
  (ej: "Menos caminata", "Evita zona de riesgo", "Más rápida").

Ejemplo de formato:
[
  {{"explanation": "...", "summary": "...", "tags": ["...", "..."]}},
  {{"explanation": "...", "summary": "...", "tags": ["...", "..."]}},
  {{"explanation": "...", "summary": "...", "tags": ["...", "..."]}}
]

Responde SOLO con el JSON, sin texto adicional."""

    @staticmethod
    def _generate_template_explanations(
        routes_data: list[dict],
        priority: str,
    ) -> list[dict]:
        """
        Fallback: explicaciones template cuando Gemini no está disponible.
        """
        explanations = []
        sorted_routes = sorted(
            enumerate(routes_data),
            key=lambda x: x[1].get("total_time_minutes", 999),
        )
        fastest_idx = sorted_routes[0][0] if sorted_routes else 0

        sorted_by_risk = sorted(
            enumerate(routes_data),
            key=lambda x: x[1].get("risk_score", 999),
        )
        safest_idx = sorted_by_risk[0][0] if sorted_by_risk else 0

        for i, route in enumerate(routes_data):
            time_min = route.get("total_time_minutes", 0)
            risk = route.get("risk_score", 0)
            modes = ", ".join(route.get("transport_modes", ["caminata"]))
            walk_km = route.get("walk_km", 0)

            tags = []
            if i == fastest_idx:
                summary = "Ruta más rápida disponible"
                tags.append("Más rápida")
                explanation = (
                    f"Esta ruta toma {time_min:.0f} minutos usando {modes}. "
                    f"Es la opción más rápida disponible."
                )
            elif i == safest_idx:
                summary = "Ruta más segura disponible"
                tags.append("Más segura")
                explanation = (
                    f"Con un score de riesgo de {risk:.0f}/100, esta es la ruta más segura. "
                    f"Toma {time_min:.0f} minutos usando {modes}."
                )
            else:
                summary = "Ruta equilibrada"
                tags.append("Equilibrada")
                explanation = (
                    f"Esta ruta balancea tiempo ({time_min:.0f} min) y seguridad "
                    f"(riesgo: {risk:.0f}/100) usando {modes}."
                )

            if walk_km < 0.5:
                tags.append("Poca caminata")
            if risk < 30:
                tags.append("Zona segura")
            if walk_km > 1.0:
                tags.append("Más caminata")

            explanations.append({
                "explanation": explanation,
                "summary": summary,
                "tags": tags[:3],
            })

        return explanations


# Singleton
gemini_service = GeminiService()
