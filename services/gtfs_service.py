"""
ConciencIA — Servicio de transporte público (GTFS estático).
Maneja estaciones de Metro, Metrobús, y otros sistemas de CDMX.
"""

import logging
import math

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# =============================================================================
# Datos estáticos de estaciones principales de CDMX
# En producción se cargarían desde archivos GTFS reales
# =============================================================================

METRO_LINES = {
    "Línea 1": {
        "color": "#E4437C",
        "stations": [
            {"name": "Observatorio", "lat": 19.3986, "lon": -99.1988},
            {"name": "Tacubaya", "lat": 19.4028, "lon": -99.1878},
            {"name": "Juanacatlán", "lat": 19.4072, "lon": -99.1802},
            {"name": "Chapultepec", "lat": 19.4205, "lon": -99.1761},
            {"name": "Sevilla", "lat": 19.4263, "lon": -99.1695},
            {"name": "Insurgentes", "lat": 19.4267, "lon": -99.1598},
            {"name": "Cuauhtémoc", "lat": 19.4269, "lon": -99.1494},
            {"name": "Balderas", "lat": 19.4270, "lon": -99.1492},
            {"name": "Salto del Agua", "lat": 19.4266, "lon": -99.1414},
            {"name": "Isabel la Católica", "lat": 19.4268, "lon": -99.1369},
            {"name": "Pino Suárez", "lat": 19.4271, "lon": -99.1328},
            {"name": "Merced", "lat": 19.4254, "lon": -99.1258},
            {"name": "Candelaria", "lat": 19.4260, "lon": -99.1195},
            {"name": "San Lázaro", "lat": 19.4276, "lon": -99.1115},
            {"name": "Moctezuma", "lat": 19.4282, "lon": -99.1020},
            {"name": "Balbuena", "lat": 19.4287, "lon": -99.0930},
            {"name": "Boulevard Puerto Aéreo", "lat": 19.4290, "lon": -99.0860},
            {"name": "Gómez Farías", "lat": 19.4270, "lon": -99.0775},
            {"name": "Zaragoza", "lat": 19.4236, "lon": -99.0685},
            {"name": "Pantitlán", "lat": 19.4164, "lon": -99.0732},
        ],
    },
    "Línea 2": {
        "color": "#0064AF",
        "stations": [
            {"name": "Cuatro Caminos", "lat": 19.4685, "lon": -99.2178},
            {"name": "Panteones", "lat": 19.4628, "lon": -99.2103},
            {"name": "Tacuba", "lat": 19.4570, "lon": -99.1940},
            {"name": "Cuitláhuac", "lat": 19.4540, "lon": -99.1870},
            {"name": "Popotla", "lat": 19.4497, "lon": -99.1821},
            {"name": "Colegio Militar", "lat": 19.4458, "lon": -99.1765},
            {"name": "Normal", "lat": 19.4434, "lon": -99.1689},
            {"name": "San Cosme", "lat": 19.4395, "lon": -99.1600},
            {"name": "Revolución", "lat": 19.4355, "lon": -99.1540},
            {"name": "Hidalgo", "lat": 19.4359, "lon": -99.1460},
            {"name": "Bellas Artes", "lat": 19.4361, "lon": -99.1411},
            {"name": "Allende", "lat": 19.4362, "lon": -99.1360},
            {"name": "Zócalo", "lat": 19.4326, "lon": -99.1332},
            {"name": "Pino Suárez", "lat": 19.4271, "lon": -99.1328},
            {"name": "San Antonio Abad", "lat": 19.4191, "lon": -99.1355},
            {"name": "Chabacano", "lat": 19.4112, "lon": -99.1392},
            {"name": "Viaducto", "lat": 19.4019, "lon": -99.1389},
            {"name": "Xola", "lat": 19.3940, "lon": -99.1387},
            {"name": "Villa de Cortés", "lat": 19.3858, "lon": -99.1385},
            {"name": "Nativitas", "lat": 19.3788, "lon": -99.1382},
            {"name": "Portales", "lat": 19.3693, "lon": -99.1380},
            {"name": "Ermita", "lat": 19.3598, "lon": -99.1377},
            {"name": "General Anaya", "lat": 19.3508, "lon": -99.1375},
            {"name": "Tasqueña", "lat": 19.3445, "lon": -99.1372},
        ],
    },
    "Línea 3": {
        "color": "#A68B2A",
        "stations": [
            {"name": "Indios Verdes", "lat": 19.4969, "lon": -99.1194},
            {"name": "Deportivo 18 de Marzo", "lat": 19.4840, "lon": -99.1250},
            {"name": "Potrero", "lat": 19.4760, "lon": -99.1290},
            {"name": "La Raza", "lat": 19.4699, "lon": -99.1340},
            {"name": "Tlatelolco", "lat": 19.4546, "lon": -99.1410},
            {"name": "Guerrero", "lat": 19.4440, "lon": -99.1448},
            {"name": "Hidalgo", "lat": 19.4359, "lon": -99.1460},
            {"name": "Juárez", "lat": 19.4282, "lon": -99.1503},
            {"name": "Balderas", "lat": 19.4270, "lon": -99.1492},
            {"name": "Niños Héroes", "lat": 19.4221, "lon": -99.1502},
            {"name": "Hospital General", "lat": 19.4147, "lon": -99.1520},
            {"name": "Centro Médico", "lat": 19.4095, "lon": -99.1548},
            {"name": "Etiopía / Plaza de la Transparencia", "lat": 19.4020, "lon": -99.1577},
            {"name": "Eugenia", "lat": 19.3918, "lon": -99.1605},
            {"name": "División del Norte", "lat": 19.3816, "lon": -99.1630},
            {"name": "Zapata", "lat": 19.3716, "lon": -99.1655},
            {"name": "Coyoacán", "lat": 19.3585, "lon": -99.1693},
            {"name": "Viveros / Derechos Humanos", "lat": 19.3478, "lon": -99.1725},
            {"name": "Miguel Ángel de Quevedo", "lat": 19.3407, "lon": -99.1752},
            {"name": "Copilco", "lat": 19.3332, "lon": -99.1780},
            {"name": "Universidad", "lat": 19.3262, "lon": -99.1803},
        ],
    },
}

METROBUS_LINES = {
    "Metrobús L1": {
        "color": "#C30D23",
        "stations": [
            {"name": "Indios Verdes", "lat": 19.4969, "lon": -99.1190},
            {"name": "Deportivo 18 de Marzo", "lat": 19.4840, "lon": -99.1245},
            {"name": "Euzkaro", "lat": 19.4714, "lon": -99.1319},
            {"name": "Eje 4 / Misterios", "lat": 19.4635, "lon": -99.1360},
            {"name": "Insurgentes / Reforma", "lat": 19.4267, "lon": -99.1598},
            {"name": "Hamburgo", "lat": 19.4234, "lon": -99.1607},
            {"name": "Sonora", "lat": 19.4157, "lon": -99.1621},
            {"name": "Campeche", "lat": 19.4098, "lon": -99.1642},
            {"name": "Chilpancingo", "lat": 19.4005, "lon": -99.1672},
            {"name": "Centro SCJN", "lat": 19.3940, "lon": -99.1685},
            {"name": "Dr. Gálvez", "lat": 19.3720, "lon": -99.1715},
            {"name": "El Caminero", "lat": 19.3242, "lon": -99.1850},
        ],
    },
    "Metrobús L4": {
        "color": "#009E4B",
        "stations": [
            {"name": "Buenavista", "lat": 19.4502, "lon": -99.1520},
            {"name": "Guerrero", "lat": 19.4440, "lon": -99.1448},
            {"name": "Hidalgo", "lat": 19.4359, "lon": -99.1460},
            {"name": "Bellas Artes", "lat": 19.4361, "lon": -99.1411},
            {"name": "20 de Noviembre", "lat": 19.4330, "lon": -99.1360},
            {"name": "Pino Suárez", "lat": 19.4271, "lon": -99.1328},
            {"name": "Jamaica", "lat": 19.4088, "lon": -99.1228},
            {"name": "Hospital Pemex", "lat": 19.3970, "lon": -99.1200},
            {"name": "Insurgentes Sur", "lat": 19.3830, "lon": -99.1710},
            {"name": "Dr. Gálvez", "lat": 19.3720, "lon": -99.1715},
        ],
    },
}

# Datos estáticos del Tren Ligero STE (Taxqueña - Xochimilco)
TREN_LIGERO_LINES = {
    "Tren Ligero": {
        "color": "#7B1FA2",
        "stations": [
            {"name": "Taxqueña", "lat": 19.3258, "lon": -99.1872},
            {"name": "Registro Federal", "lat": 19.3195, "lon": -99.1825},
            {"name": "Estadio Azteca", "lat": 19.3028, "lon": -99.1506},
            {"name": "Tlalpan", "lat": 19.2897, "lon": -99.1658},
            {"name": "Huipulco", "lat": 19.2947, "lon": -99.1428},
            {"name": "Xotepingo", "lat": 19.2825, "lon": -99.1356},
            {"name": "Nativitas", "lat": 19.2758, "lon": -99.1289},
            {"name": "Xochimilco", "lat": 19.2577, "lon": -99.1036},
        ],
    },
}

# Línea 12 del Metro (sur-oriente CDMX: Mixcoac - Tláhuac)
METRO_LINE_12 = {
    "Línea 12": {
        "color": "#D4AC0D",
        "stations": [
            {"name": "Mixcoac", "lat": 19.3749, "lon": -99.1952},
            {"name": "Insurgentes Sur", "lat": 19.3698, "lon": -99.1882},
            {"name": "Hospital 20 de Noviembre", "lat": 19.3620, "lon": -99.1793},
            {"name": "Zapotitlán", "lat": 19.3300, "lon": -99.0620},
            {"name": "Nopalera", "lat": 19.3193, "lon": -99.0530},
            {"name": "Olivos", "lat": 19.3100, "lon": -99.0450},
            {"name": "Periferico Oriente", "lat": 19.3020, "lon": -99.0380},
            {"name": "Tláhuac", "lat": 19.2912, "lon": -99.0155},
        ],
    },
}



class GTFSService:
    """
    Servicio de transporte público basado en datos estáticos.
    Calcula tiempos estimados y encuentra estaciones cercanas.
    """

    def __init__(self):
        self._all_stations: list[dict] | None = None

    def _get_all_stations(self) -> list[dict]:
        """Compila todas las estaciones de todos los sistemas."""
        if self._all_stations is None:
            stations = []
            for line_name, line_data in METRO_LINES.items():
                for station in line_data["stations"]:
                    stations.append({
                        "name": station["name"],
                        "lat": station["lat"],
                        "lon": station["lon"],
                        "system": "METRO",
                        "line": line_name,
                        "color": line_data["color"],
                    })
            for line_name, line_data in METRO_LINE_12.items():
                for station in line_data["stations"]:
                    stations.append({
                        "name": station["name"],
                        "lat": station["lat"],
                        "lon": station["lon"],
                        "system": "METRO",
                        "line": line_name,
                        "color": line_data["color"],
                    })
            for line_name, line_data in METROBUS_LINES.items():
                for station in line_data["stations"]:
                    stations.append({
                        "name": station["name"],
                        "lat": station["lat"],
                        "lon": station["lon"],
                        "system": "METROBUS",
                        "line": line_name,
                        "color": line_data["color"],
                    })
            for line_name, line_data in TREN_LIGERO_LINES.items():
                for station in line_data["stations"]:
                    stations.append({
                        "name": station["name"],
                        "lat": station["lat"],
                        "lon": station["lon"],
                        "system": "LIGHT_RAIL",
                        "line": line_name,
                        "color": line_data["color"],
                    })
            self._all_stations = stations
        return self._all_stations


    def find_nearest_stations(
        self,
        lat: float,
        lon: float,
        max_distance_km: float = 1.0,
        limit: int = 5,
    ) -> list[dict]:
        """
        Encuentra las estaciones más cercanas a un punto.

        Returns:
            Lista de estaciones ordenadas por distancia con campo 'distance_km'.
        """
        stations = self._get_all_stations()
        results = []

        for station in stations:
            dist = self._haversine_km(lat, lon, station["lat"], station["lon"])
            if dist <= max_distance_km:
                results.append({**station, "distance_km": round(dist, 3)})

        results.sort(key=lambda x: x["distance_km"])
        return results[:limit]

    def estimate_transit_time(
        self,
        origin_station: dict,
        dest_station: dict,
    ) -> dict:
        """
        Estima tiempo de viaje en transporte público entre dos estaciones.

        Usa heurísticas basadas en:
        - Velocidad promedio del Metro CDMX: ~35 km/h
        - Velocidad promedio del Metrobús: ~20 km/h
        - Tiempo promedio entre estaciones: ~2.5 min (Metro), ~3 min (Metrobús)
        - Tiempo de transbordo: ~5 minutos
        """
        system = origin_station.get("system", "METRO")
        origin_line = origin_station.get("line", "")
        dest_line = dest_station.get("line", "")

        # Contar estaciones entre origen y destino en la misma línea
        same_line = origin_line == dest_line
        needs_transfer = not same_line

        if same_line:
            num_stops = self._count_stops_between(
                origin_station, dest_station, origin_line
            )
        else:
            # Simplificación: estimar con distancia directa
            dist = self._haversine_km(
                origin_station["lat"], origin_station["lon"],
                dest_station["lat"], dest_station["lon"],
            )
            if system == "METRO":
                num_stops = max(1, int(dist / 0.8))  # ~0.8 km entre estaciones
            else:
                num_stops = max(1, int(dist / 0.6))

        # Calcular tiempo
        if system == "METRO":
            time_per_stop = 2.5  # minutos
        else:
            time_per_stop = 3.0

        travel_time = num_stops * time_per_stop
        transfer_time = 5.0 if needs_transfer else 0
        wait_time = 4.0  # Tiempo promedio de espera

        total_time = travel_time + transfer_time + wait_time

        return {
            "travel_time_minutes": round(travel_time, 1),
            "wait_time_minutes": wait_time,
            "transfer_time_minutes": transfer_time,
            "total_time_minutes": round(total_time, 1),
            "num_stops": num_stops,
            "needs_transfer": needs_transfer,
            "origin_line": origin_line,
            "dest_line": dest_line,
        }

    def _count_stops_between(
        self, origin: dict, dest: dict, line_name: str
    ) -> int:
        """Cuenta el número de estaciones entre dos paradas en la misma línea."""
        # Buscar en Metro
        if line_name in METRO_LINES:
            stations = METRO_LINES[line_name]["stations"]
        elif line_name in METROBUS_LINES:
            stations = METROBUS_LINES[line_name]["stations"]
        else:
            return 5  # Fallback

        origin_idx = None
        dest_idx = None
        for i, s in enumerate(stations):
            if s["name"] == origin.get("name"):
                origin_idx = i
            if s["name"] == dest.get("name"):
                dest_idx = i

        if origin_idx is not None and dest_idx is not None:
            return abs(dest_idx - origin_idx)
        return 5  # Fallback

    def get_transit_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> dict | None:
        """
        Intenta construir una ruta usando transporte público.

        Returns:
            Dict con segmentos (caminar → transporte → caminar) o None si no viable.
        """
        # Encontrar estaciones cercanas al origen y destino
        origin_stations = self.find_nearest_stations(
            origin_lat, origin_lon, max_distance_km=1.5, limit=3
        )
        dest_stations = self.find_nearest_stations(
            dest_lat, dest_lon, max_distance_km=1.5, limit=3
        )

        if not origin_stations or not dest_stations:
            return None

        # Evaluar combinaciones y escoger la mejor
        best_route = None
        best_time = float("inf")

        for orig_st in origin_stations:
            for dest_st in dest_stations:
                # Tiempo caminando a la estación de origen
                walk_to = self._haversine_km(
                    origin_lat, origin_lon, orig_st["lat"], orig_st["lon"]
                ) / 5.0 * 60  # 5 km/h caminando → minutos

                # Tiempo en transporte
                transit = self.estimate_transit_time(orig_st, dest_st)

                # Tiempo caminando desde la estación de destino
                walk_from = self._haversine_km(
                    dest_st["lat"], dest_st["lon"], dest_lat, dest_lon
                ) / 5.0 * 60

                total = walk_to + transit["total_time_minutes"] + walk_from

                if total < best_time:
                    best_time = total
                    best_route = {
                        "origin_station": orig_st,
                        "dest_station": dest_st,
                        "walk_to_minutes": round(walk_to, 1),
                        "transit": transit,
                        "walk_from_minutes": round(walk_from, 1),
                        "total_time_minutes": round(total, 1),
                        "walk_to_km": round(
                            self._haversine_km(
                                origin_lat, origin_lon,
                                orig_st["lat"], orig_st["lon"]
                            ), 2
                        ),
                        "walk_from_km": round(
                            self._haversine_km(
                                dest_st["lat"], dest_st["lon"],
                                dest_lat, dest_lon
                            ), 2
                        ),
                    }

        return best_route

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
gtfs_service = GTFSService()
