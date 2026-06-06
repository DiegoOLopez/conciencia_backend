"""
ConciencIA — Servicio de datos abiertos CDMX.
Consulta incidentes viales y datos de movilidad de la CDMX.
"""

import logging
import math
from typing import Any

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Datos de ejemplo de zonas con incidencia vial alta en CDMX
# En producción, esto vendría de datos abiertos reales de SEMOVI/SSC
ZONAS_ALTO_RIESGO_CDMX = [
    # (lat, lon, radio_km, nombre, nivel_riesgo 0-100)
    (19.4326, -99.1332, 1.0, "Centro Histórico", 65),
    (19.3937, -99.0906, 1.5, "Iztapalapa Centro", 70),
    (19.4969, -99.1467, 1.0, "Indios Verdes", 60),
    (19.3586, -99.1640, 1.0, "Coyoacán Centro", 35),
    (19.4284, -99.1683, 0.8, "Roma-Condesa", 30),
    (19.3610, -99.0869, 1.5, "Tláhuac", 72),
    (19.4437, -99.0686, 1.5, "Nezahualcóyotl (límite)", 68),
    (19.4833, -99.1200, 1.0, "La Villa", 55),
    (19.5100, -99.1467, 1.2, "Gustavo A. Madero Norte", 62),
    (19.3300, -99.1900, 1.0, "Tlalpan Sur", 45),
    (19.4100, -99.1800, 0.8, "Mixcoac", 40),
    (19.3700, -99.2600, 1.5, "Santa Fe", 50),
    (19.4600, -99.0700, 1.2, "Aragón", 58),
    (19.4900, -99.2100, 1.0, "Azcapotzalco", 52),
    (19.2836, -99.1369, 0.9, "Huipulco / Tec CCM", 38),
    (19.2944, -99.1627, 0.9, "Tlalpan Centro", 42),
]


class CDMXDataService:
    """Servicio para consultar datos urbanos de CDMX."""

    def __init__(self):
        self._incidents_cache: list[dict] = []
        self._cache_timestamp: float = 0

    def get_risk_for_point(self, lat: float, lon: float) -> dict[str, Any]:
        """
        Calcula el nivel de riesgo para un punto geográfico
        basado en zonas conocidas de incidencia.

        Returns:
            Dict con 'risk_level' (0-100), 'zone_name', 'factors'.
        """
        max_risk = 0
        nearest_zone = None
        factors = []

        for zone_lat, zone_lon, radio_km, nombre, nivel in ZONAS_ALTO_RIESGO_CDMX:
            dist = self._haversine_km(lat, lon, zone_lat, zone_lon)

            if dist <= radio_km:
                # Dentro de la zona — riesgo proporcional a cercanía al centro
                proximity_factor = 1 - (dist / radio_km)
                adjusted_risk = nivel * proximity_factor

                if adjusted_risk > max_risk:
                    max_risk = adjusted_risk
                    nearest_zone = nombre
                    factors.append(f"Zona {nombre} (riesgo base: {nivel})")

        # Riesgo mínimo baseline para cualquier punto de CDMX
        baseline_risk = 15
        final_risk = max(baseline_risk, min(100, max_risk))

        return {
            "risk_level": round(final_risk, 1),
            "zone_name": nearest_zone or "Zona sin datos específicos",
            "factors": factors or ["Riesgo base urbano"],
        }

    def get_risk_for_segment(
        self,
        points: list[list[float]],
        hour: int,
    ) -> dict[str, Any]:
        """
        Calcula riesgo promedio para un segmento de ruta (lista de puntos).

        Args:
            points: Lista de [lat, lon]
            hour: Hora del día (0-23)

        Returns:
            Dict con 'risk_score', 'max_risk_point', 'factors'.
        """
        if not points:
            return {"risk_score": 0, "max_risk_point": None, "factors": []}

        # Samplear puntos para no evaluar todos (performance)
        sample_size = min(len(points), 10)
        step = max(1, len(points) // sample_size)
        sampled_points = points[::step]

        risks = []
        max_risk = 0
        max_risk_point = None
        all_factors = set()

        for point in sampled_points:
            risk_data = self.get_risk_for_point(point[0], point[1])
            risk = risk_data["risk_level"]
            risks.append(risk)

            if risk > max_risk:
                max_risk = risk
                max_risk_point = point

            all_factors.update(risk_data["factors"])

        # Ajuste por hora
        hour_multiplier = self._get_hour_risk_multiplier(hour)
        avg_risk = sum(risks) / len(risks) if risks else 0
        adjusted_risk = min(100, avg_risk * hour_multiplier)

        return {
            "risk_score": round(adjusted_risk, 1),
            "max_risk_point": max_risk_point,
            "factors": list(all_factors),
            "hour_multiplier": hour_multiplier,
        }

    @staticmethod
    def _get_hour_risk_multiplier(hour: int) -> float:
        """
        Multiplicador de riesgo según hora del día.
        Las horas nocturnas tienen mayor riesgo.
        """
        if 6 <= hour < 10:    # Mañana temprana
            return 0.9
        elif 10 <= hour < 17:  # Día
            return 0.8
        elif 17 <= hour < 20:  # Tarde
            return 1.0
        elif 20 <= hour < 22:  # Noche temprana
            return 1.3
        elif 22 <= hour or hour < 1:  # Noche
            return 1.6
        else:  # Madrugada (1-6)
            return 1.8

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Distancia Haversine entre dos puntos en kilómetros."""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        return R * c


# Singleton
cdmx_data_service = CDMXDataService()
