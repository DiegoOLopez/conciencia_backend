"""
ConciencIA — Servicio LLM (OpenRouter / Gemini).
Wrapper async para generación de explicaciones de rutas.
"""

import json
import logging
import time
import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class GeminiService:
    """Wrapper para OpenRouter / LLM para el Agente Explicador."""

    def __init__(self):
        self._configured = False
        self._api_key = None
        self._model_name = None
        self._client: httpx.AsyncClient | None = None

    def _ensure_configured(self):
        """Configura el LLM al primer uso."""
        if not self._configured:
            if settings.OPENROUTER_API_KEY:
                self._api_key = settings.OPENROUTER_API_KEY
                self._model_name = settings.OPENROUTER_MODEL
                logger.info(f"OpenRouter configurado con modelo: {self._model_name}")
            elif settings.GEMINI_API_KEY:
                # Opcional: Fallback si quisieras seguir usando la librería de gemini directo
                pass
            
            if not self._api_key:
                logger.warning(
                    "API key no configurada. "
                    "El Agente Explicador usará respuestas template."
                )
            
            self._client = httpx.AsyncClient(timeout=15.0)
            self._configured = True

    async def generate_explanations(
        self,
        routes_data: list[dict],
        priority: str,
        departure_hour: int,
    ) -> list[dict]:
        """Genera explicaciones en lenguaje natural para las rutas."""
        self._ensure_configured()

        if not self._api_key:
            return self._generate_template_explanations(routes_data, priority)

        prompt = self._build_prompt(routes_data, priority, departure_hour)

        try:
            start_time = time.time()
            
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": self._model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.7,
                "max_tokens": 1024,
            }
            
            response = await self._client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"OpenRouter respondió en {elapsed_ms:.0f}ms")

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Parsear respuesta JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # A veces el modelo regresa json con bloques markdown
                clean_content = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(clean_content)

            # Dependiendo si viene como array o dict con 'routes'
            if isinstance(result, list) and len(result) >= len(routes_data):
                return result[:len(routes_data)]
            elif isinstance(result, dict):
                # Maneja keys como 'routes' o cualquier otra
                for key in result:
                    if isinstance(result[key], list) and len(result[key]) >= len(routes_data):
                        return result[key][:len(routes_data)]
                return self._generate_template_explanations(routes_data, priority)
            else:
                logger.warning("Respuesta del LLM con formato inesperado, usando template")
                return self._generate_template_explanations(routes_data, priority)

        except Exception as e:
            logger.error(f"Error al generar explicaciones con LLM: {e}")
            return self._generate_template_explanations(routes_data, priority)

    async def generate_pedestrian_explanations(
        self,
        metrics: dict,
        priority_label: str
    ) -> dict:
        """Genera explicaciones para el agente peatonal OSMnx."""
        self._ensure_configured()

        if not self._api_key:
            return {
                "resumen_una_linea": f"Ruta {priority_label}",
                "explicacion_ia": "Explicación no disponible (API Key faltante).",
                "tags": ["peatonal"]
            }

        prompt = f"""Eres un agente experto en ruteo peatonal urbano en CDMX.
Se calculó una ruta con la prioridad "{priority_label}".
Métricas de la ruta:
- Distancia: {metrics['distancia_metros']}m
- Tiempo: {metrics['tiempo_minutos']} min
- Escaleras: {"Sí" if metrics['tiene_escaleras'] else "No"}
- Score de Accesibilidad: {metrics['score_accesibilidad']}/100

Genera un objeto JSON con:
- "resumen_una_linea": string de máximo 8 palabras resumiendo la ruta.
- "explicacion_ia": string con 2-3 oraciones que explique por qué es adecuada para la prioridad "{priority_label}". Menciona accesibilidad, infraestructura (banquetas) o distancia/tiempo. ¡OBLIGATORIO: NO menciones seguridad vial, índices de delincuencia, zonas peligrosas ni ningún indicador de riesgo!
- "tags": lista de 1-3 etiquetas descriptivas cortas en español (ej: "sin escaleras", "más rápida").

Responde SOLO con el JSON válido."""

        try:
            headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self._model_name,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.6,
                "max_tokens": 512,
            }
            
            response = await self._client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            content = response.json()["choices"][0]["message"]["content"]
            try:
                result = json.loads(content)
            except:
                clean_content = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(clean_content)
            return result
        except Exception as e:
            logger.error(f"Error LLM peatonal: {e}")
            return {
                "resumen_una_linea": f"Ruta {priority_label}",
                "explicacion_ia": "Ruta generada automáticamente.",
                "tags": []
            }

    async def generate_pedestrian_recommendation(
        self,
        winner_id: str,
        winner_score: float,
        routes_metrics: dict,
        priority: str
    ) -> str:
        """Genera la razón de la recomendación de la ruta peatonal."""
        if not self._client:
            return "Recomendada en base a la prioridad seleccionada."

        prompt = f"""Eres un experto en movilidad peatonal. Se calcularon 3 rutas y la '{winner_id}' obtuvo el mayor score ({winner_score}) para la prioridad '{priority}'.
Métricas de todas las rutas:
{json.dumps(routes_metrics, indent=2)}

Redacta la razón para recomendar la ruta '{winner_id}'.
Reglas inamovibles:
- Máximo 2 oraciones.
- Hablar al usuario de tú, directo.
- Mencionar exactamente una ventaja basada en datos reales de las métricas (tiempo_minutos, score_accesibilidad, tiene_escaleras, distancia_metros).
- Mencionar un trade-off si existe (ej. es más larga) — si no hay ninguno relevante, omitirlo.
- NUNCA mencionar seguridad vial, riesgo, peligrosidad ni delincuencia.
- Si todas las rutas tienen scores muy similares (diferencia < 2 puntos), dilo: "Las tres rutas son muy similares; cualquiera funciona bien para tu trayecto."

Responde SOLO con un objeto JSON en este formato exacto:
{{"razon": "Tu texto aquí"}}
"""
        
        try:
            payload = {
                "model": "google/gemini-2.5-flash-preview",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
                "max_tokens": 150,
            }
            
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "ConciencIA"
            }
            
            response = await self._client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            content = response.json()["choices"][0]["message"]["content"]
            try:
                result = json.loads(content)
            except:
                clean_content = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(clean_content)
            return result.get("razon", "Ruta óptima seleccionada.")
        except Exception as e:
            logger.error(f"Error LLM recomendacion peatonal: {e}")
            return "Ruta recomendada basada en las métricas de OSMnx."

    def _build_prompt(
        self,
        routes_data: list[dict],
        priority: str,
        departure_hour: int,
    ) -> str:
        """Construye el prompt para el LLM."""
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

Genera un objeto JSON con una propiedad "routes" que contenga una lista de objetos (uno por ruta).
Cada objeto debe tener:
- "explanation": string con 2-3 oraciones comparando la ruta con las demás. Menciona trade-offs concretos de tiempo vs seguridad. Habla en español, tono amigable y conciso.
- "summary": string de máximo 8 palabras resumiendo la ruta.
- "tags": lista de 1-3 etiquetas descriptivas cortas en español (ej: "Menos caminata", "Evita zona de riesgo", "Más rápida").

Responde SOLO con el JSON válido, sin texto adicional."""

    @staticmethod
    def _generate_template_explanations(
        routes_data: list[dict],
        priority: str,
    ) -> list[dict]:
        """Fallback: explicaciones template."""
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
