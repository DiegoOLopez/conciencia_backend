"""
ConciencIA — Clase base para agentes.
Define la interfaz común y funcionalidad compartida.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any


class AgentContext:
    """Contexto compartido entre agentes durante una solicitud."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.data: dict[str, Any] = {}
        self.logs: list[str] = []
        self.errors: list[str] = []

    def set(self, key: str, value: Any):
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def log(self, message: str):
        self.logs.append(message)

    def add_error(self, error: str):
        self.errors.append(error)


class AgentResult:
    """Resultado de la ejecución de un agente."""

    def __init__(
        self,
        success: bool,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        execution_time_ms: float = 0,
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.execution_time_ms = execution_time_ms


class BaseAgent(ABC):
    """
    Clase base abstracta para todos los agentes de ConciencIA.

    Provee:
    - Logging estructurado por agente
    - Medición automática de tiempo de ejecución
    - Manejo de errores con fallback
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")

    async def run(self, context: AgentContext) -> AgentResult:
        """
        Ejecuta el agente con medición de tiempo y manejo de errores.
        Los subclases implementan `execute()`.
        """
        self.logger.info(f"[{context.request_id}] Agente '{self.name}' iniciando...")
        start = time.time()

        try:
            result = await self.execute(context)
            elapsed = (time.time() - start) * 1000

            result.execution_time_ms = elapsed
            context.log(f"Agente '{self.name}' completado en {elapsed:.0f}ms")
            self.logger.info(
                f"[{context.request_id}] Agente '{self.name}' completado en {elapsed:.0f}ms"
            )
            return result

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            error_msg = f"Agente '{self.name}' falló: {str(e)}"
            self.logger.error(f"[{context.request_id}] {error_msg}", exc_info=True)
            context.add_error(error_msg)

            # Intentar fallback
            try:
                fallback_result = await self.fallback(context, e)
                fallback_result.execution_time_ms = elapsed
                return fallback_result
            except Exception:
                return AgentResult(
                    success=False,
                    error=error_msg,
                    execution_time_ms=elapsed,
                )

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Lógica principal del agente. Debe ser implementada por subclases."""
        ...

    async def fallback(self, context: AgentContext, error: Exception) -> AgentResult:
        """
        Lógica de fallback cuando execute() falla.
        Puede ser sobreescrita por subclases.
        """
        return AgentResult(
            success=False,
            error=f"Sin fallback disponible: {str(error)}",
        )
