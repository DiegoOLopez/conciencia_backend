"""
ConciencIA — Agente Especializado en Ruteo Peatonal (OSMnx).
"""

import math
import logging
import networkx as nx
import osmnx as ox
from typing import Dict, Any, List, Tuple

from schemas.request import TravelPriority, RouteRequest
from schemas.pedestrian import (
    PedestrianResponse,
    PedestrianRoute,
    PedestrianMetrics,
    PedestrianInstruction,
    PedestrianCoordinate,
    PedestrianMetadata,
    PedestrianRecommendation
)
from services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

# Caché en memoria para evitar descargar el grafo múltiples veces
_graph_cache: Dict[str, Any] = {
    "graph": None,
    "center_lat": None,
    "center_lon": None,
}

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia en metros entre dos coordenadas."""
    R = 6371000  # Radio de la tierra en metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class PedestrianAgent:
    """Agente para ruteo peatonal con OSMnx."""

    def __init__(self):
        self.logger = logger
        # Optimización de osmnx
        ox.settings.log_console = False
        ox.settings.use_cache = True

    def _get_graph(self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> nx.MultiDiGraph:
        """Obtiene o descarga el grafo peatonal cubriendo origen y destino."""
        # Punto medio
        center_lat = (origin_lat + dest_lat) / 2
        center_lon = (origin_lon + dest_lon) / 2

        # Si tenemos un grafo cacheado, revisamos si ambos puntos están dentro de un radio de ~2.5km del centro
        if _graph_cache["graph"] is not None:
            dist_orig = haversine(center_lat, center_lon, _graph_cache["center_lat"], _graph_cache["center_lon"])
            if dist_orig < 2000:
                self.logger.info("Usando grafo OSMnx desde caché en memoria.")
                return _graph_cache["graph"]

        self.logger.info(f"Descargando grafo OSMnx walk_network para centro {center_lat}, {center_lon}...")
        try:
            # Según el prompt: usar dist=3000, network_type="walk", simplify=True
            G = ox.graph_from_point(
                center_point=(center_lat, center_lon),
                dist=3000,
                network_type="walk",
                simplify=True
            )
            
            # Guardar en caché
            _graph_cache["graph"] = G
            _graph_cache["center_lat"] = center_lat
            _graph_cache["center_lon"] = center_lon
            
            return G
        except Exception as e:
            self.logger.error(f"Error descargando grafo: {e}")
            raise RuntimeError("GRAPH_DOWNLOAD_FAILED")

    def _calcular_peso_accesibilidad(self, data: dict) -> float:
        base = data.get("length", 0)
        penalizacion = 0

        highway = data.get("highway", "")
        surface = data.get("surface", "")
        incline = data.get("incline", "")

        superficies_malas = ["cobblestone", "sett", "gravel", "dirt", "unpaved", "grass"]
        if surface in superficies_malas:
            penalizacion += base * 0.5

        if highway == "steps":
            penalizacion += base * 2.0  # penalización severa

        if isinstance(incline, str) and "%" in incline:
            try:
                grado = abs(float(incline.replace("%", "")))
                if grado > 8:
                    penalizacion += base * 0.8
                elif grado > 5:
                    penalizacion += base * 0.3
            except ValueError:
                pass

        sidewalk = data.get("sidewalk", "")
        footway = data.get("footway", "")
        if sidewalk in ["both", "yes"] or footway == "sidewalk":
            penalizacion -= base * 0.1

        return max(base + penalizacion, 1)

    def _calcular_peso_balanceado(self, data: dict) -> float:
        longitud = data.get("length", 0)
        tiempo = longitud / 1.25  # segundos
        accesibilidad = self._calcular_peso_accesibilidad(data)

        peso_tiempo = tiempo / 60
        peso_acc = accesibilidad / 100

        return (0.6 * peso_tiempo) + (0.4 * peso_acc)

    def _preparar_pesos_grafo(self, G: nx.MultiDiGraph):
        """Asigna los pesos a todas las aristas del grafo."""
        for u, v, k, data in G.edges(data=True, keys=True):
            longitud = data.get("length", 0)
            data["travel_time"] = longitud / 1.25
            data["accessibility_weight"] = self._calcular_peso_accesibilidad(data)
            data["balanced_weight"] = self._calcular_peso_balanceado(data)

    def _calcular_metricas(self, G: nx.MultiDiGraph, ruta_nodos: list) -> dict:
        aristas = list(zip(ruta_nodos[:-1], ruta_nodos[1:]))

        distancia_total = 0
        tiempo_total = 0
        tiene_escaleras = False
        superficies_irregulares = 0
        total_aristas = len(aristas)

        for u, v in aristas:
            data = min(G[u][v].values(), key=lambda d: d.get("length", 0))

            distancia_total += data.get("length", 0)
            tiempo_total += data.get("length", 0) / 1.25

            if data.get("highway") == "steps":
                tiene_escaleras = True

            if data.get("surface") in ["cobblestone", "sett", "gravel", "dirt", "unpaved"]:
                superficies_irregulares += 1

        penalizaciones = 0
        if tiene_escaleras:
            penalizaciones += 40
        penalizaciones += min((superficies_irregulares / max(total_aristas, 1)) * 60, 60)
        score_accesibilidad = max(100 - penalizaciones, 0)

        return {
            "distancia_metros": round(distancia_total),
            "tiempo_segundos": round(tiempo_total),
            "tiempo_minutos": round(tiempo_total / 60, 1),
            "tiene_escaleras": tiene_escaleras,
            "score_accesibilidad": round(score_accesibilidad)
        }

    def _ruta_a_coordenadas(self, G: nx.MultiDiGraph, ruta_nodos: list) -> list:
        coordenadas = []
        for nodo in ruta_nodos:
            datos_nodo = G.nodes[nodo]
            coordenadas.append(PedestrianCoordinate(
                lat=datos_nodo["y"],
                lon=datos_nodo["x"]
            ))
        return coordenadas

    def _generar_instrucciones(self, G: nx.MultiDiGraph, ruta_nodos: list) -> list:
        instrucciones = []
        instrucciones.append(PedestrianInstruction(
            texto="Comienza a caminar desde tu punto de origen",
            distancia_metros=0
        ))

        for i in range(1, len(ruta_nodos) - 1):
            nodo_actual = ruta_nodos[i]
            arista_data = min(G[ruta_nodos[i-1]][nodo_actual].values(),
                              key=lambda d: d.get("length", 0))

            nombre_calle = arista_data.get("name", "")
            if isinstance(nombre_calle, list):
                nombre_calle = nombre_calle[0]
                
            longitud = arista_data.get("length", 0)
            highway = arista_data.get("highway", "")

            if highway == "steps":
                instrucciones.append(PedestrianInstruction(
                    texto=f"Sube/baja escaleras ({round(longitud)}m)",
                    distancia_metros=round(longitud)
                ))
            elif nombre_calle:
                instrucciones.append(PedestrianInstruction(
                    texto=f"Continúa por {nombre_calle} ({round(longitud)}m)",
                    distancia_metros=round(longitud)
                ))

        instrucciones.append(PedestrianInstruction(
            texto="Has llegado a tu destino",
            distancia_metros=0
        ))

        return instrucciones

    def _score_recomendacion(self, G: nx.MultiDiGraph, ruta_nodos: list, priority: str) -> float:
        score = 0
        aristas = list(zip(ruta_nodos[:-1], ruta_nodos[1:]))
        
        for u, v in aristas:
            data = min(G[u][v].values(), key=lambda d: d.get("length", 0))

            longitud = data.get("length", 0)
            grade_abs = data.get("grade_abs", 0)
            highway = data.get("highway", "")
            surface = data.get("surface", "")
            smoothness = data.get("smoothness", "")
            lit = data.get("lit", "")
            width = data.get("width", None)
            sidewalk = data.get("sidewalk", "")
            tactile = data.get("tactile_paving", "")
            footway = data.get("footway", "")

            if highway in ["pedestrian", "footway", "path"]:
                score += 2
            if sidewalk in ["both", "yes"]:
                score += 1
            if lit == "yes":
                score += 1
            if smoothness in ["excellent", "good"]:
                score += 1
            if tactile == "yes":
                score += 1
            if footway == "sidewalk":
                score += 1

            if highway == "steps":
                score -= 4
            if surface in ["cobblestone", "sett", "gravel", "dirt", "unpaved", "grass"]:
                score -= 2
            if smoothness in ["bad", "very_bad", "horrible"]:
                score -= 2
            if grade_abs > 0.10:
                score -= 3
            elif grade_abs > 0.05:
                score -= 1

            if priority in ["FASTEST", "SPEED"]:
                score -= longitud * 0.001
            elif priority == "ACCESSIBLE":
                if highway == "steps":
                    score -= 4
                if grade_abs > 0.08:
                    score -= 3
                if tactile == "yes":
                    score += 2
                if width and isinstance(width, (int, float, str)):
                    try:
                        if float(width) >= 2.0:
                            score += 1
                    except ValueError:
                        pass
            elif priority == "SHORTEST":
                score -= longitud * 0.002

        return round(score, 2)

    async def calculate_routes(self, request: RouteRequest) -> PedestrianResponse:
        """Flujo principal del agente peatonal."""
        try:
            G = self._get_graph(
                request.origin.lat, request.origin.lon,
                request.destination.lat, request.destination.lon
            )
            
            # Asegurarse de que los nodos estén a menos de 500m del grafo
            nodo_origen = ox.nearest_nodes(G, X=request.origin.lon, Y=request.origin.lat)
            nodo_destino = ox.nearest_nodes(G, X=request.destination.lon, Y=request.destination.lat)
            
            # Simple check of node proximity
            o_data = G.nodes[nodo_origen]
            d_data = G.nodes[nodo_destino]
            if haversine(request.origin.lat, request.origin.lon, o_data["y"], o_data["x"]) > 500 or \
               haversine(request.destination.lat, request.destination.lon, d_data["y"], d_data["x"]) > 500:
                return PedestrianResponse(
                    error=True,
                    codigo="NODES_TOO_FAR",
                    mensaje="Los nodos más cercanos en la red están a más de 500m del punto solicitado."
                )

            self._preparar_pesos_grafo(G)

            # Prioridades a calcular
            priority = request.priority
            rutas_config = []
            
            if priority in [TravelPriority.FASTEST, TravelPriority.SPEED]:
                rutas_config = [
                    ("ruta_1", "Más rápida", "travel_time"),
                    ("ruta_2", "Balance", "balanced_weight"),
                    ("ruta_3", "Más corta", "length")
                ]
            elif priority == TravelPriority.SHORTEST:
                rutas_config = [
                    ("ruta_1", "Más corta", "length"),
                    ("ruta_2", "Más rápida", "travel_time"),
                    ("ruta_3", "Balance", "balanced_weight")
                ]
            elif priority == TravelPriority.ACCESSIBLE:
                rutas_config = [
                    ("ruta_1", "Más accesible", "accessibility_weight"),
                    ("ruta_2", "Balance", "balanced_weight"),
                    ("ruta_3", "Más rápida", "travel_time")
                ]
            else: # BALANCED
                rutas_config = [
                    ("ruta_1", "Balance", "balanced_weight"),
                    ("ruta_2", "Más rápida", "travel_time"),
                    ("ruta_3", "Más accesible", "accessibility_weight")
                ]

            rutas_finales = []
            scores_recomendacion = {}
            metricas_all = {}
            
            for r_id, r_label, weight_attr in rutas_config:
                try:
                    ruta_nodos = nx.shortest_path(G, nodo_origen, nodo_destino, weight=weight_attr)
                    metricas_dict = self._calcular_metricas(G, ruta_nodos)
                    
                    score = self._score_recomendacion(G, ruta_nodos, priority.name if hasattr(priority, 'name') else str(priority))
                    scores_recomendacion[r_id] = score
                    metricas_all[r_id] = metricas_dict
                    
                    coords = self._ruta_a_coordenadas(G, ruta_nodos)
                    instrucciones = self._generar_instrucciones(G, ruta_nodos)
                    
                    metricas = PedestrianMetrics(**metricas_dict)
                    
                    # Llamar al LLM para la explicación
                    llm_response = await gemini_service.generate_pedestrian_explanations(
                        metrics=metricas_dict,
                        priority_label=r_label
                    )
                    
                    rutas_finales.append(PedestrianRoute(
                        id=r_id,
                        prioridad_label=r_label,
                        resumen_una_linea=llm_response.get("resumen_una_linea", "Ruta disponible"),
                        explicacion_ia=llm_response.get("explicacion_ia", "Ruta peatonal generada automáticamente."),
                        tags=llm_response.get("tags", []),
                        metricas=metricas,
                        coordenadas_polyline=coords,
                        instrucciones=instrucciones,
                        tiene_escaleras=metricas_dict["tiene_escaleras"]
                    ))
                except nx.NetworkXNoPath:
                    continue # Try next

            if not rutas_finales:
                return PedestrianResponse(
                    error=True,
                    codigo="NO_PATH_FOUND",
                    mensaje="No se encontró una ruta peatonal entre los puntos indicados."
                )

            recomendacion = None
            if scores_recomendacion:
                winner_id = max(scores_recomendacion, key=scores_recomendacion.get)
                winner_score = scores_recomendacion[winner_id]
                razon = await gemini_service.generate_pedestrian_recommendation(
                    winner_id=winner_id,
                    winner_score=winner_score,
                    routes_metrics=metricas_all,
                    priority=priority.value
                )
                
                recomendacion = PedestrianRecommendation(
                    ruta_id=winner_id,
                    score=winner_score,
                    razon=razon
                )

            metadata = PedestrianMetadata(
                origen=PedestrianCoordinate(lat=request.origin.lat, lon=request.origin.lon),
                destino=PedestrianCoordinate(lat=request.destination.lat, lon=request.destination.lon),
                priority_solicitada=priority.value
            )

            return PedestrianResponse(rutas=rutas_finales, recomendacion=recomendacion, metadata=metadata)

        except RuntimeError as e:
            return PedestrianResponse(
                error=True,
                codigo=str(e),
                mensaje="Ocurrió un error al obtener la red peatonal."
            )
        except Exception as e:
            self.logger.error(f"Error inesperado en ruteo peatonal: {e}", exc_info=True)
            return PedestrianResponse(
                error=True,
                codigo="UNKNOWN_ERROR",
                mensaje="Error interno al calcular la ruta."
            )

pedestrian_agent = PedestrianAgent()
