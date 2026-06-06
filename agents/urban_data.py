"""
ConciencIA — Agente 2: Datos Urbanos.
Recopila y normaliza información urbana de CDMX para las rutas.
"""

from agents.base import BaseAgent, AgentContext, AgentResult
from services.osm_service import osm_service, OSMService
from services.gtfs_service import gtfs_service
from services.cdmx_data_service import cdmx_data_service
from services.tlalpan_transit_service import tlalpan_transit_service
from schemas.request import TransportMode


class UrbanDataAgent(BaseAgent):
    """
    Agente de datos urbanos.

    Responsabilidades:
    - Obtener rutas peatonales y vehiculares de OSRM
    - Buscar estaciones de transporte público cercanas
    - Construir rutas multimodales candidatas
    - Recopilar datos de riesgo vial de la zona
    """

    def __init__(self):
        super().__init__("urban_data")

    async def execute(self, context: AgentContext) -> AgentResult:
        request = context.get("request")
        sanitized = context.get("sanitized_request", {})

        if not request:
            return AgentResult(success=False, error="No se recibió request")

        origin_lat = sanitized.get("origin_lat", request.origin.lat)
        origin_lon = sanitized.get("origin_lon", request.origin.lon)
        dest_lat = sanitized.get("dest_lat", request.destination.lat)
        dest_lon = sanitized.get("dest_lon", request.destination.lon)

        allowed_modes = set(request.transport_modes)
        candidate_routes = []

        # ======================================================================
        # 1. Rutas peatonales (OSRM foot profile)
        # Solo si la distancia es razonable a pie (máx 4 km).
        # Para rutas largas el usuario necesita transporte, no caminar.
        # ======================================================================
        MAX_WALK_STANDALONE_KM = 4.0
        if TransportMode.WALK in allowed_modes:
            self.logger.info("Consultando OSRM para rutas peatonales...")
            osrm_walking = await osm_service.get_walking_route(
                origin_lat, origin_lon, dest_lat, dest_lon
            )
            walking_routes = OSMService.extract_routes_from_osrm(osrm_walking, "foot")

            for i, route in enumerate(walking_routes[:3]):
                dist = route["distance_km"]
                if dist > MAX_WALK_STANDALONE_KM:
                    self.logger.info(
                        f"Descartando ruta peatonal: {dist:.1f} km (máx {MAX_WALK_STANDALONE_KM} km)"
                    )
                    continue  # No agregar rutas irrazonablemente largas
                candidate_routes.append({
                    "type": "walking",
                    "id": f"walk_{i}",
                    "modes": [TransportMode.WALK.value],
                    "segments": [{
                        "mode": TransportMode.WALK.value,
                        "coordinates": route["coordinates"],
                        "distance_km": dist,
                        "duration_minutes": route["duration_minutes"],
                        "description": self._describe_walking_route(route),
                    }],
                    "total_distance_km": dist,
                    "total_time_minutes": route["duration_minutes"],
                    "walk_km": dist,
                    "transfers": 0,
                })

        # ======================================================================
        # 2. Rutas con transporte público (Metro / Metrobús)
        # ======================================================================
        transit_modes = {TransportMode.METRO, TransportMode.METROBUS, TransportMode.BUS}
        if allowed_modes & transit_modes:
            self.logger.info("Buscando rutas de transporte público...")
            transit_route = gtfs_service.get_transit_route(
                origin_lat, origin_lon, dest_lat, dest_lon
            )

            if transit_route:
                origin_st = transit_route["origin_station"]
                dest_st = transit_route["dest_station"]
                transit_info = transit_route["transit"]

                segments = []

                # Segmento 1: Caminar al transporte
                if transit_route["walk_to_km"] > 0.05:
                    osrm_w1 = await osm_service.get_walking_route(
                        origin_lat, origin_lon, origin_st["lat"], origin_st["lon"]
                    )
                    r_w1 = OSMService.extract_routes_from_osrm(osrm_w1, "foot")
                    walk_to_coords = r_w1[0]["coordinates"] if r_w1 else [
                        [origin_lat, origin_lon],
                        [origin_st["lat"], origin_st["lon"]],
                    ]
                    segments.append({
                        "mode": TransportMode.WALK.value,
                        "coordinates": walk_to_coords,
                        "distance_km": transit_route["walk_to_km"],
                        "duration_minutes": transit_route["walk_to_minutes"],
                        "description": f"Caminar a estación {origin_st['name']}",
                    })

                # Segmento 2: Transporte público
                system = origin_st.get("system", "METRO")
                if system == "METRO":
                    transit_mode = TransportMode.METRO.value
                elif system == "METROBUS":
                    transit_mode = TransportMode.METROBUS.value
                elif system == "LIGHT_RAIL":
                    transit_mode = TransportMode.LIGHT_RAIL.value
                else:
                    transit_mode = TransportMode.METRO.value
                
                osrm_t = await osm_service.get_driving_route(
                    origin_st["lat"], origin_st["lon"], dest_st["lat"], dest_st["lon"]
                )
                r_t = OSMService.extract_routes_from_osrm(osrm_t, "car")
                transit_coords = r_t[0]["coordinates"] if r_t else [
                    [origin_st["lat"], origin_st["lon"]],
                    [dest_st["lat"], dest_st["lon"]],
                ]
                
                segments.append({
                    "mode": transit_mode,
                    "coordinates": transit_coords,
                    "distance_km": round(
                        gtfs_service._haversine_km(
                            origin_st["lat"], origin_st["lon"],
                            dest_st["lat"], dest_st["lon"]
                        ), 2
                    ),
                    "duration_minutes": transit_info["travel_time_minutes"],
                    "description": (
                        f"{origin_st['line']}: {origin_st['name']} → {dest_st['name']} "
                        f"({transit_info['num_stops']} estaciones)"
                    ),
                    "transit_line": origin_st["line"],
                    "transit_stops": transit_info["num_stops"],
                })

                # Segmento 3: Caminar desde el transporte
                if transit_route["walk_from_km"] > 0.05:
                    osrm_w2 = await osm_service.get_walking_route(
                        dest_st["lat"], dest_st["lon"], dest_lat, dest_lon
                    )
                    r_w2 = OSMService.extract_routes_from_osrm(osrm_w2, "foot")
                    walk_from_coords = r_w2[0]["coordinates"] if r_w2 else [
                        [dest_st["lat"], dest_st["lon"]],
                        [dest_lat, dest_lon],
                    ]
                    segments.append({
                        "mode": TransportMode.WALK.value,
                        "coordinates": walk_from_coords,
                        "distance_km": transit_route["walk_from_km"],
                        "duration_minutes": transit_route["walk_from_minutes"],
                        "description": f"Caminar desde estación {dest_st['name']} al destino",
                    })

                total_walk = transit_route["walk_to_km"] + transit_route["walk_from_km"]
                total_dist = total_walk + segments[len(segments) // 2]["distance_km"]
                modes_used = list({s["mode"] for s in segments})

                candidate_routes.append({
                    "type": "transit",
                    "id": f"transit_0",
                    "modes": modes_used,
                    "segments": segments,
                    "total_distance_km": round(total_dist, 2),
                    "total_time_minutes": transit_route["total_time_minutes"],
                    "walk_km": round(total_walk, 2),
                    "transfers": 1 if transit_info["needs_transfer"] else 0,
                })

        # ======================================================================
        # 3. Rutas con Tren Ligero (Tlalpan)
        # ======================================================================
        if TransportMode.LIGHT_RAIL in allowed_modes:
            self.logger.info("Buscando rutas con Tren Ligero...")
            # Ampliar radio a 5km: cubre caminata + traslado en metro hasta Taxqueña
            light_rail_route = tlalpan_transit_service.get_light_rail_route(
                origin_lat, origin_lon, dest_lat, dest_lon, max_walk_km=5.0
            )

            if light_rail_route:
                origin_st = light_rail_route["origin_station"]
                dest_st = light_rail_route["dest_station"]
                transit_info = light_rail_route["transit"]

                segments = []

                # Segmento 1: Caminar al Tren Ligero
                if light_rail_route["walk_to_km"] > 0.05:
                    osrm_w1 = await osm_service.get_walking_route(
                        origin_lat, origin_lon, origin_st["lat"], origin_st["lon"]
                    )
                    r_w1 = OSMService.extract_routes_from_osrm(osrm_w1, "foot")
                    walk_to_coords = r_w1[0]["coordinates"] if r_w1 else [
                        [origin_lat, origin_lon],
                        [origin_st["lat"], origin_st["lon"]],
                    ]
                    segments.append({
                        "mode": TransportMode.WALK.value,
                        "coordinates": walk_to_coords,
                        "distance_km": light_rail_route["walk_to_km"],
                        "duration_minutes": light_rail_route["walk_to_minutes"],
                        "description": f"Caminar a estación {origin_st['name']}",
                    })

                # Segmento 2: Tren Ligero
                osrm_t = await osm_service.get_driving_route(
                    origin_st["lat"], origin_st["lon"], dest_st["lat"], dest_st["lon"]
                )
                r_t = OSMService.extract_routes_from_osrm(osrm_t, "car")
                transit_coords = r_t[0]["coordinates"] if r_t else [
                    [origin_st["lat"], origin_st["lon"]],
                    [dest_st["lat"], dest_st["lon"]],
                ]
                
                segments.append({
                    "mode": TransportMode.LIGHT_RAIL.value,
                    "coordinates": transit_coords,
                    "distance_km": transit_info["distance_km"],
                    "duration_minutes": transit_info["travel_time_minutes"],
                    "description": (
                        f"{transit_info['line']}: {origin_st['name']} → {dest_st['name']} "
                        f"({transit_info['num_stops']} estaciones)"
                    ),
                    "transit_line": transit_info["line"],
                    "transit_stops": transit_info["num_stops"],
                })

                # Segmento 3: Caminar desde el Tren Ligero
                if light_rail_route["walk_from_km"] > 0.05:
                    osrm_w2 = await osm_service.get_walking_route(
                        dest_st["lat"], dest_st["lon"], dest_lat, dest_lon
                    )
                    r_w2 = OSMService.extract_routes_from_osrm(osrm_w2, "foot")
                    walk_from_coords = r_w2[0]["coordinates"] if r_w2 else [
                        [dest_st["lat"], dest_st["lon"]],
                        [dest_lat, dest_lon],
                    ]
                    segments.append({
                        "mode": TransportMode.WALK.value,
                        "coordinates": walk_from_coords,
                        "distance_km": light_rail_route["walk_from_km"],
                        "duration_minutes": light_rail_route["walk_from_minutes"],
                        "description": f"Caminar desde estación {dest_st['name']} al destino",
                    })

                total_walk = light_rail_route["walk_to_km"] + light_rail_route["walk_from_km"]
                total_dist = total_walk + transit_info["distance_km"]
                modes_used = list({s["mode"] for s in segments})

                candidate_routes.append({
                    "type": "light_rail",
                    "id": "light_rail_0",
                    "modes": modes_used,
                    "segments": segments,
                    "total_distance_km": round(total_dist, 2),
                    "total_time_minutes": light_rail_route["total_time_minutes"],
                    "walk_km": round(total_walk, 2),
                    "transfers": 0,
                })

        # ======================================================================
        # 4. Rutas con RTP (Red de Transporte de Pasajeros - Tlalpan)
        # ======================================================================
        if TransportMode.RTP in allowed_modes:
            self.logger.info("Buscando rutas con RTP...")
            # Ampliar radio a 3km para rutas largas
            rtp_routes = tlalpan_transit_service.get_rtp_routes(
                origin_lat, origin_lon, dest_lat, dest_lon, max_walk_km=3.0
            )

            for idx, rtp_route in enumerate(rtp_routes[:2]):  # Máximo 2 rutas RTP
                origin_st = rtp_route["origin_station"]
                dest_st = rtp_route["dest_station"]
                transit_info = rtp_route["transit"]

                segments = []

                # Segmento 1: Caminar a la parada RTP
                if rtp_route["walk_to_km"] > 0.05:
                    osrm_w1 = await osm_service.get_walking_route(
                        origin_lat, origin_lon, origin_st["lat"], origin_st["lon"]
                    )
                    r_w1 = OSMService.extract_routes_from_osrm(osrm_w1, "foot")
                    walk_to_coords = r_w1[0]["coordinates"] if r_w1 else [
                        [origin_lat, origin_lon],
                        [origin_st["lat"], origin_st["lon"]],
                    ]
                    segments.append({
                        "mode": TransportMode.WALK.value,
                        "coordinates": walk_to_coords,
                        "distance_km": rtp_route["walk_to_km"],
                        "duration_minutes": rtp_route["walk_to_minutes"],
                        "description": f"Caminar a parada {origin_st['name']}",
                    })

                # Segmento 2: RTP
                osrm_t = await osm_service.get_driving_route(
                    origin_st["lat"], origin_st["lon"], dest_st["lat"], dest_st["lon"]
                )
                r_t = OSMService.extract_routes_from_osrm(osrm_t, "car")
                transit_coords = r_t[0]["coordinates"] if r_t else [
                    [origin_st["lat"], origin_st["lon"]],
                    [dest_st["lat"], dest_st["lon"]],
                ]
                
                segments.append({
                    "mode": TransportMode.RTP.value,
                    "coordinates": transit_coords,
                    "distance_km": transit_info["distance_km"],
                    "duration_minutes": transit_info["travel_time_minutes"],
                    "description": (
                        f"{transit_info['line']}: {origin_st['name']} → {dest_st['name']} "
                        f"({transit_info['num_stops']} paradas)"
                    ),
                    "transit_line": transit_info["line"],
                    "transit_stops": transit_info["num_stops"],
                })

                # Segmento 3: Caminar desde la parada RTP
                if rtp_route["walk_from_km"] > 0.05:
                    osrm_w2 = await osm_service.get_walking_route(
                        dest_st["lat"], dest_st["lon"], dest_lat, dest_lon
                    )
                    r_w2 = OSMService.extract_routes_from_osrm(osrm_w2, "foot")
                    walk_from_coords = r_w2[0]["coordinates"] if r_w2 else [
                        [dest_st["lat"], dest_st["lon"]],
                        [dest_lat, dest_lon],
                    ]
                    segments.append({
                        "mode": TransportMode.WALK.value,
                        "coordinates": walk_from_coords,
                        "distance_km": rtp_route["walk_from_km"],
                        "duration_minutes": rtp_route["walk_from_minutes"],
                        "description": f"Caminar desde parada {dest_st['name']} al destino",
                    })

                total_walk = rtp_route["walk_to_km"] + rtp_route["walk_from_km"]
                total_dist = total_walk + transit_info["distance_km"]
                modes_used = list({s["mode"] for s in segments})

                candidate_routes.append({
                    "type": "rtp",
                    "id": f"rtp_{idx}",
                    "modes": modes_used,
                    "segments": segments,
                    "total_distance_km": round(total_dist, 2),
                    "total_time_minutes": rtp_route["total_time_minutes"],
                    "walk_km": round(total_walk, 2),
                    "transfers": 0,
                })

        # ======================================================================
        # 5. Rutas vehiculares (si se permite)
        # ======================================================================
        if TransportMode.CAR in allowed_modes:
            self.logger.info("Consultando OSRM para rutas vehiculares...")
            osrm_driving = await osm_service.get_driving_route(
                origin_lat, origin_lon, dest_lat, dest_lon
            )
            driving_routes = OSMService.extract_routes_from_osrm(osrm_driving, "car")

            for i, route in enumerate(driving_routes[:2]):
                candidate_routes.append({
                    "type": "driving",
                    "id": f"car_{i}",
                    "modes": [TransportMode.CAR.value],
                    "segments": [{
                        "mode": TransportMode.CAR.value,
                        "coordinates": route["coordinates"],
                        "distance_km": route["distance_km"],
                        "duration_minutes": route["duration_minutes"],
                        "description": self._describe_driving_route(route),
                    }],
                    "total_distance_km": route["distance_km"],
                    "total_time_minutes": route["duration_minutes"],
                    "walk_km": 0,
                    "transfers": 0,
                })

        # ======================================================================
        # 6. Datos de riesgo por zona
        # ======================================================================
        hour = request.departure_time.hour
        zone_risks = {
            "origin": cdmx_data_service.get_risk_for_point(origin_lat, origin_lon),
            "destination": cdmx_data_service.get_risk_for_point(dest_lat, dest_lon),
        }

        self.logger.info(
            f"Recopilados {len(candidate_routes)} rutas candidatas. "
            f"Riesgo origen: {zone_risks['origin']['risk_level']}, "
            f"Riesgo destino: {zone_risks['destination']['risk_level']}"
        )

        context.set("candidate_routes", candidate_routes)
        context.set("zone_risks", zone_risks)
        context.set("departure_hour", hour)

        return AgentResult(
            success=True,
            data={
                "num_candidates": len(candidate_routes),
                "route_types": [r["type"] for r in candidate_routes],
                "zone_risks": zone_risks,
            },
        )

    @staticmethod
    def _describe_walking_route(route: dict) -> str:
        """Genera descripción legible de una ruta peatonal."""
        dist = route["distance_km"]
        dur = route["duration_minutes"]
        # Intentar obtener nombre de calle principal
        main_street = ""
        for step in route.get("steps", []):
            name = step.get("name", "")
            if name and name != "":
                main_street = f" por {name}"
                break
        return f"Caminar {dist:.1f} km (~{dur:.0f} min){main_street}"

    @staticmethod
    def _describe_driving_route(route: dict) -> str:
        """Genera descripción legible de una ruta vehicular."""
        dist = route["distance_km"]
        dur = route["duration_minutes"]
        return f"Conducir {dist:.1f} km (~{dur:.0f} min)"
