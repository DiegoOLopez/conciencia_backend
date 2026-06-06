"""
ConciencIA — Schemas para ruteo peatonal con OSMnx.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class PedestrianCoordinate(BaseModel):
    lat: float
    lon: float


class PedestrianInstruction(BaseModel):
    texto: str
    distancia_metros: int


class PedestrianMetrics(BaseModel):
    distancia_metros: int
    tiempo_minutos: float
    score_accesibilidad: int


class PedestrianRoute(BaseModel):
    id: str
    prioridad_label: str
    resumen_una_linea: str
    explicacion_ia: str
    tags: List[str]
    metricas: PedestrianMetrics
    coordenadas_polyline: List[PedestrianCoordinate]
    instrucciones: List[PedestrianInstruction]
    tiene_escaleras: bool


class PedestrianMetadata(BaseModel):
    origen: PedestrianCoordinate
    destino: PedestrianCoordinate
    priority_solicitada: str
    network_type: str = "walk"
    osmnx_version: str = "1.x"


class PedestrianResponse(BaseModel):
    rutas: List[PedestrianRoute] = []
    metadata: Optional[PedestrianMetadata] = None
    error: bool = False
    codigo: Optional[str] = None
    mensaje: Optional[str] = None
