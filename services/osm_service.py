"""
ConciencIA — Servicio de OpenStreetMap / OSRM.
Obtiene grafos de calles y rutas candidatas para CDMX.
"""

import logging
from typing import Any

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OSMService:
    """Interacción con OSRM público y datos de OpenStreetMap."""

    # Velocidades realistas para CDMX (el OSRM público devuelve duraciones de auto
    # incluso con perfil 'foot', así que recalculamos desde la distancia)
    SPEED_KMH = {
        "foot": 4.8,    # Promedio real caminando en ciudad ~4.5-5 km/h
        "car": 22.0,    # Promedio CDMX con tráfico ~20-25 km/h
        "bike": 14.0,   # Promedio en bicicleta urbana
    }

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.OSRM_BASE_URL,
                timeout=30.0,
            )
        return self._client

    async def get_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        profile: str = "foot",
        alternatives: bool = True,
    ) -> dict[str, Any]:
        """
        Obtiene rutas de OSRM.

        Args:
            origin_lat, origin_lon: Coordenadas de origen
            dest_lat, dest_lon: Coordenadas de destino
            profile: 'foot' (peatón), 'car', 'bike'
            alternatives: Si True, pide rutas alternativas

        Returns:
            Respuesta de OSRM con rutas, geometrías y duraciones.
        """
        client = await self._get_client()
        coords = f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"

        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "alternatives": "true" if alternatives else "false",
        }
        
        # El servidor público router.project-osrm.org a menudo devuelve rutas
        # de auto para perfil foot. Usamos routing.openstreetmap.de que tiene
        # grafos de red separados y precisos por modo.
        base_url = f"https://routing.openstreetmap.de/routed-{profile}"
        url = f"{base_url}/route/v1/driving/{coords}"

        try:
            # Quitamos la barra inicial para que reemplace completamente el base_url
            # del cliente si estuviera configurado, o simplemente enviamos URL completa.
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "Ok":
                logger.error(f"OSRM error: {data.get('code')} - {data.get('message')}")
                return {"routes": [], "code": data.get("code")}

            logger.info(
                f"OSRM devolvió {len(data.get('routes', []))} rutas "
                f"para profile={profile}"
            )
            return data

        except httpx.HTTPError as e:
            logger.error(f"Error al consultar OSRM: {e}")
            return {"routes": [], "code": "Error", "message": str(e)}

    async def get_walking_route(
        self, origin_lat: float, origin_lon: float,
        dest_lat: float, dest_lon: float,
    ) -> dict[str, Any]:
        """Ruta peatonal con alternativas."""
        return await self.get_route(
            origin_lat, origin_lon, dest_lat, dest_lon,
            profile="foot", alternatives=True,
        )

    async def get_driving_route(
        self, origin_lat: float, origin_lon: float,
        dest_lat: float, dest_lon: float,
    ) -> dict[str, Any]:
        """Ruta vehicular con alternativas."""
        return await self.get_route(
            origin_lat, origin_lon, dest_lat, dest_lon,
            profile="car", alternatives=True,
        )

    @staticmethod
    def extract_routes_from_osrm(
        osrm_response: dict,
        profile: str = "foot",
    ) -> list[dict]:
        """
        Extrae rutas limpias de la respuesta OSRM.
        
        IMPORTANTE: El OSRM público devuelve duraciones vehiculares incluso
        para el perfil 'foot'. Recalculamos la duración desde la distancia
        con velocidades realistas para CDMX.

        Returns:
            Lista de dicts con 'coordinates', 'distance_km', 'duration_minutes', 'steps'.
        """
        speed_kmh = OSMService.SPEED_KMH.get(profile, OSMService.SPEED_KMH["foot"])
        routes = []
        for route in osrm_response.get("routes", []):
            geometry = route.get("geometry", {})
            coords = geometry.get("coordinates", [])

            # OSRM devuelve [lon, lat], convertimos a [lat, lon]
            coords_latlon = [[c[1], c[0]] for c in coords]

            distance_km = route.get("distance", 0) / 1000
            # Recalcular duración con velocidad realista (ignora la de OSRM)
            duration_minutes = (distance_km / speed_kmh) * 60 if distance_km > 0 else 0

            # Extraer pasos con instrucciones
            steps = []
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    step_coords = step.get("geometry", {}).get("coordinates", [])
                    step_coords_latlon = [[c[1], c[0]] for c in step_coords]
                    step_dist_km = step.get("distance", 0) / 1000
                    step_dur = (step_dist_km / speed_kmh) * 60 if step_dist_km > 0 else 0
                    steps.append({
                        "name": step.get("name", ""),
                        "distance_km": step_dist_km,
                        "duration_minutes": round(step_dur, 1),
                        "coordinates": step_coords_latlon,
                        "maneuver": step.get("maneuver", {}),
                    })

            routes.append({
                "coordinates": coords_latlon,
                "distance_km": round(distance_km, 3),
                "duration_minutes": round(duration_minutes, 1),
                "steps": steps,
            })

        return routes

    async def close(self):
        """Cierra el cliente HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton
osm_service = OSMService()
