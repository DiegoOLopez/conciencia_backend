"""
ConciencIA — Servicio de Transporte de Tlalpan.
Maneja datos de Tren Ligero y RTP específicos para la zona de Tlalpan.
"""

import json
import math
from pathlib import Path
from typing import Optional


class TlalpanTransitService:
    """Servicio para gestionar transporte público en Tlalpan (Tren Ligero y RTP)."""

    def __init__(self):
        """Inicializa el servicio cargando datos estáticos."""
        data_path = Path(__file__).parent.parent / "data" / "tlalpan_transit.json"
        with open(data_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        
        self.light_rail = self.data["light_rail"]
        self.rtp_lines = self.data["rtp_lines"]

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distancia en km entre dos coordenadas usando fórmula de Haversine."""
        R = 6371  # Radio de la Tierra en km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    def find_nearest_station(
        self,
        lat: float,
        lon: float,
        system: str = "LIGHT_RAIL",
        max_distance_km: float = 2.0
    ) -> Optional[dict]:
        """
        Encuentra la estación más cercana a un punto.
        
        Args:
            lat: Latitud del punto
            lon: Longitud del punto
            system: Sistema de transporte ("LIGHT_RAIL" o "RTP")
            max_distance_km: Distancia máxima de búsqueda
            
        Returns:
            Diccionario con información de la estación más cercana o None
        """
        stations = []
        
        if system == "LIGHT_RAIL":
            stations = self.light_rail["stations"]
        elif system == "RTP":
            # Recopilar todas las paradas de todas las líneas RTP
            for line in self.rtp_lines:
                for stop in line["stops"]:
                    stop_with_line = stop.copy()
                    stop_with_line["line"] = line["line"]
                    stop_with_line["line_name"] = line["name"]
                    stations.append(stop_with_line)
        
        if not stations:
            return None
        
        # Encontrar la estación más cercana
        nearest = None
        min_distance = float('inf')
        
        for station in stations:
            distance = self._haversine_km(lat, lon, station["lat"], station["lon"])
            if distance < min_distance and distance <= max_distance_km:
                min_distance = distance
                nearest = {
                    **station,
                    "distance_km": round(distance, 2),
                    "system": system,
                }
        
        return nearest

    def get_light_rail_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        max_walk_km: float = 1.5
    ) -> Optional[dict]:
        """
        Busca una ruta usando el Tren Ligero.
        
        Args:
            origin_lat: Latitud de origen
            origin_lon: Longitud de origen
            dest_lat: Latitud de destino
            dest_lon: Longitud de destino
            max_walk_km: Distancia máxima de caminata a estaciones
            
        Returns:
            Diccionario con información de la ruta o None si no es viable
        """
        # Buscar estaciones cercanas al origen y destino
        origin_station = self.find_nearest_station(
            origin_lat, origin_lon, "LIGHT_RAIL", max_walk_km
        )
        dest_station = self.find_nearest_station(
            dest_lat, dest_lon, "LIGHT_RAIL", max_walk_km
        )
        
        if not origin_station or not dest_station:
            return None
        
        # Verificar que no sean la misma estación
        if origin_station["id"] == dest_station["id"]:
            return None
        
        # Calcular número de estaciones entre origen y destino
        origin_order = origin_station["order"]
        dest_order = dest_station["order"]
        num_stops = abs(dest_order - origin_order)
        
        if num_stops == 0:
            return None
        
        # Calcular distancia y tiempo en el tren
        transit_distance = self._haversine_km(
            origin_station["lat"], origin_station["lon"],
            dest_station["lat"], dest_station["lon"]
        )
        
        # Tiempo = distancia / velocidad + tiempo de paradas (1 min por estación)
        travel_time_minutes = (
            (transit_distance / self.light_rail["avg_speed_kmh"]) * 60 +
            num_stops * 1.0  # 1 minuto por parada
        )
        
        # Calcular tiempos de caminata (5 km/h promedio)
        walk_to_minutes = (origin_station["distance_km"] / 5.0) * 60
        walk_from_minutes = (dest_station["distance_km"] / 5.0) * 60
        
        return {
            "origin_station": origin_station,
            "dest_station": dest_station,
            "transit": {
                "line": self.light_rail["line"],
                "system": "LIGHT_RAIL",
                "num_stops": num_stops,
                "distance_km": round(transit_distance, 2),
                "travel_time_minutes": round(travel_time_minutes, 1),
                "frequency_minutes": self.light_rail["frequency_minutes"],
            },
            "walk_to_km": origin_station["distance_km"],
            "walk_to_minutes": round(walk_to_minutes, 1),
            "walk_from_km": dest_station["distance_km"],
            "walk_from_minutes": round(walk_from_minutes, 1),
            "total_time_minutes": round(
                walk_to_minutes + travel_time_minutes + walk_from_minutes +
                self.light_rail["frequency_minutes"] / 2,  # Tiempo de espera promedio
                1
            ),
        }

    def get_rtp_routes(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        max_walk_km: float = 1.0
    ) -> list[dict]:
        """
        Busca rutas usando líneas RTP.
        
        Args:
            origin_lat: Latitud de origen
            origin_lon: Longitud de origen
            dest_lat: Latitud de destino
            dest_lon: Longitud de destino
            max_walk_km: Distancia máxima de caminata a paradas
            
        Returns:
            Lista de rutas RTP viables
        """
        viable_routes = []
        
        for line in self.rtp_lines:
            # Buscar paradas cercanas al origen y destino en esta línea
            origin_stop = None
            dest_stop = None
            min_origin_dist = float('inf')
            min_dest_dist = float('inf')
            
            for stop in line["stops"]:
                # Distancia al origen
                dist_to_origin = self._haversine_km(
                    origin_lat, origin_lon, stop["lat"], stop["lon"]
                )
                if dist_to_origin < min_origin_dist and dist_to_origin <= max_walk_km:
                    min_origin_dist = dist_to_origin
                    origin_stop = {**stop, "distance_km": round(dist_to_origin, 2)}
                
                # Distancia al destino
                dist_to_dest = self._haversine_km(
                    dest_lat, dest_lon, stop["lat"], stop["lon"]
                )
                if dist_to_dest < min_dest_dist and dist_to_dest <= max_walk_km:
                    min_dest_dist = dist_to_dest
                    dest_stop = {**stop, "distance_km": round(dist_to_dest, 2)}
            
            # Verificar si encontramos paradas viables
            if not origin_stop or not dest_stop:
                continue
            
            # Verificar que no sean la misma parada
            if origin_stop["id"] == dest_stop["id"]:
                continue
            
            # Verificar que el destino esté después del origen en la ruta
            if dest_stop["order"] <= origin_stop["order"]:
                continue
            
            # Calcular detalles de la ruta
            num_stops = dest_stop["order"] - origin_stop["order"]
            transit_distance = self._haversine_km(
                origin_stop["lat"], origin_stop["lon"],
                dest_stop["lat"], dest_stop["lon"]
            )
            
            travel_time_minutes = (
                (transit_distance / line["avg_speed_kmh"]) * 60 +
                num_stops * 1.5  # 1.5 minutos por parada
            )
            
            walk_to_minutes = (origin_stop["distance_km"] / 5.0) * 60
            walk_from_minutes = (dest_stop["distance_km"] / 5.0) * 60
            
            viable_routes.append({
                "origin_station": {**origin_stop, "system": "RTP", "line": line["line"]},
                "dest_station": {**dest_stop, "system": "RTP", "line": line["line"]},
                "transit": {
                    "line": line["line"],
                    "line_name": line["name"],
                    "system": "RTP",
                    "num_stops": num_stops,
                    "distance_km": round(transit_distance, 2),
                    "travel_time_minutes": round(travel_time_minutes, 1),
                    "frequency_minutes": line["frequency_minutes"],
                },
                "walk_to_km": origin_stop["distance_km"],
                "walk_to_minutes": round(walk_to_minutes, 1),
                "walk_from_km": dest_stop["distance_km"],
                "walk_from_minutes": round(walk_from_minutes, 1),
                "total_time_minutes": round(
                    walk_to_minutes + travel_time_minutes + walk_from_minutes +
                    line["frequency_minutes"] / 2,  # Tiempo de espera promedio
                    1
                ),
            })
        
        # Ordenar por tiempo total
        viable_routes.sort(key=lambda r: r["total_time_minutes"])
        
        return viable_routes


# Instancia global del servicio
tlalpan_transit_service = TlalpanTransitService()

# Made with Bob
