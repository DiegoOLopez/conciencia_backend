"""
ConciencIA — Schemas de response.
Contratos Pydantic para las respuestas enviadas a la app Flutter.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from schemas.request import TransportMode


class Segment(BaseModel):
    """Un segmento individual de una ruta (caminar, metro, bus, etc.)."""
    mode: TransportMode = Field(description="Modo de transporte de este segmento")
    polyline: list[list[float]] = Field(
        description="Lista de coordenadas [lat, lon] del segmento",
    )
    distance_km: float = Field(ge=0, description="Distancia en km")
    duration_minutes: float = Field(ge=0, description="Duración en minutos")
    risk_score: float = Field(
        ge=0, le=100,
        description="Score de riesgo del segmento (0=seguro, 100=peligroso)",
    )
    description: str = Field(
        description="Descripción legible del segmento",
        examples=["Caminar por Av. Insurgentes Sur hacia el norte"],
    )
    transit_line: str | None = Field(
        default=None,
        description="Línea de transporte (ej: 'Línea 1', 'Metrobús L3')",
    )
    transit_stops: int | None = Field(
        default=None,
        description="Número de estaciones/paradas en este segmento",
    )


class RouteOption(BaseModel):
    """Una opción de ruta completa con scores y explicación."""
    rank: int = Field(ge=1, le=3, description="Posición en el ranking (1=mejor)")
    segments: list[Segment] = Field(description="Segmentos de la ruta")
    total_time_minutes: float = Field(ge=0, description="Tiempo total en minutos")
    total_distance_km: float = Field(ge=0, description="Distancia total en km")
    risk_score: float = Field(
        ge=0, le=100,
        description="Score de riesgo total (0=seguro, 100=peligroso)",
    )
    accessibility_score: float = Field(
        ge=0, le=100,
        description="Score de accesibilidad (0=inaccesible, 100=muy accesible)",
    )
    explanation: str = Field(
        description="Explicación en lenguaje natural del Agente Explicador",
    )
    summary: str = Field(
        description="Resumen de una línea de la ruta",
        examples=["Metro + 5 min caminata — ruta más rápida"],
    )
    transport_modes_used: list[TransportMode] = Field(
        description="Modos de transporte utilizados en esta ruta",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Etiquetas descriptivas (ej: 'Menos caminata', 'Evita zona de riesgo')",
    )


class RouteResponse(BaseModel):
    """Respuesta completa con las 3 mejores rutas."""
    routes: list[RouteOption] = Field(
        description="Las 3 mejores rutas ordenadas por relevancia",
    )
    request_id: str = Field(description="ID anónimo de la solicitud (UUID)")
    computed_at: datetime = Field(description="Timestamp de la computación")
    computation_time_ms: float = Field(
        ge=0,
        description="Tiempo total de cómputo en milisegundos",
    )
