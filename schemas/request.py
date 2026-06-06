"""
ConciencIA — Schemas de request.
Contratos Pydantic para las solicitudes entrantes de la app Flutter.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TransportMode(str, Enum):
    """Modos de transporte disponibles en CDMX."""
    WALK = "WALK"
    BIKE = "BIKE"
    LIGHT_RAIL = "LIGHT_RAIL"  # Tren Ligero (Taxqueña - Xochimilco)
    RTP = "RTP"                 # Red de Transporte de Pasajeros (Tlalpan)
    # Modos legacy (mantener para compatibilidad)
    BUS = "BUS"
    METRO = "METRO"
    METROBUS = "METROBUS"
    TROLLEYBUS = "TROLLEYBUS"
    CAR = "CAR"


class TravelPriority(str, Enum):
    """Prioridad del usuario para la optimización de ruta."""
    SPEED = "SPEED"           # Lo más rápido (legacy)
    FASTEST = "FASTEST"       # Lo más rápido (OSMnx)
    SAFETY = "SAFETY"         # Lo más seguro (legacy)
    BALANCED = "BALANCED"     # Equilibrio (Ambos)
    SHORTEST = "SHORTEST"     # Más corto en distancia
    ACCESSIBLE = "ACCESSIBLE" # Más accesible (evita escaleras/mal piso)


class Coordinate(BaseModel):
    """Coordenada geográfica validada para CDMX."""
    lat: float = Field(
        ge=19.0, le=19.6,
        description="Latitud dentro de CDMX",
        examples=[19.4326],
    )
    lon: float = Field(
        ge=-99.5, le=-98.9,
        description="Longitud dentro de CDMX",
        examples=[-99.1332],
    )


class RouteRequest(BaseModel):
    """Solicitud de ruta del usuario."""
    origin: Coordinate = Field(description="Punto de origen")
    destination: Coordinate = Field(description="Punto de destino")
    departure_time: datetime = Field(
        description="Hora de salida deseada",
        examples=["2026-06-06T08:00:00"],
    )
    transport_modes: list[TransportMode] = Field(
        default=[TransportMode.WALK, TransportMode.METRO, TransportMode.METROBUS],
        description="Modos de transporte permitidos",
        min_length=1,
    )
    priority: TravelPriority = Field(
        default=TravelPriority.BALANCED,
        description="Prioridad de optimización",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "origin": {"lat": 19.4326, "lon": -99.1332},
                    "destination": {"lat": 19.4285, "lon": -99.1677},
                    "departure_time": "2026-06-06T08:00:00",
                    "transport_modes": ["WALK", "METRO"],
                    "priority": "BALANCED",
                }
            ]
        }
    }
