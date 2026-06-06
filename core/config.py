"""
ConciencIA — Configuración centralizada del backend.
Usa pydantic-settings para cargar variables de entorno.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración del backend cargada desde variables de entorno / .env"""

    # --- API ---
    APP_NAME: str = "ConciencIA API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # --- CORS ---
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    # --- Google Gemini ---
    GEMINI_API_KEY: str = Field(default="", description="API key de Google Gemini")
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # --- OSRM (routing) ---
    OSRM_BASE_URL: str = "https://router.project-osrm.org"

    # --- Datos CDMX ---
    CDMX_INCIDENTS_URL: str = (
        "https://datos.cdmx.gob.mx/api/3/action/datastore_search"
    )

    # --- Límites geográficos CDMX ---
    CDMX_LAT_MIN: float = 19.0
    CDMX_LAT_MAX: float = 19.6
    CDMX_LON_MIN: float = -99.5
    CDMX_LON_MAX: float = -98.9

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> Settings:
    """Singleton cacheado de la configuración."""
    return Settings()
