"""
ConciencIA — Agente 6: Privacidad y Seguridad.
Valida que los requests no contengan datos sensibles y minimiza datos.
"""

import re
import uuid

from agents.base import BaseAgent, AgentContext, AgentResult
from core.security import truncate_coordinate, validate_cdmx_coordinates


class PrivacyAgent(BaseAgent):
    """
    Agente de privacidad y seguridad.

    Responsabilidades:
    - Verificar que no se incluyan datos sensibles
    - Truncar coordenadas para minimización de datos
    - Generar request_id anónimo
    - Validar coordenadas dentro de CDMX
    """

    # Patrones para detectar datos sensibles
    SENSITIVE_PATTERNS = [
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "email"),
        (re.compile(r"\b\d{10}\b"), "teléfono (10 dígitos)"),
        (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "teléfono"),
        (re.compile(r"\b\d{13,18}\b"), "CURP/INE potencial"),
    ]

    def __init__(self):
        super().__init__("privacy")

    async def execute(self, context: AgentContext) -> AgentResult:
        request = context.get("request")
        if not request:
            return AgentResult(success=False, error="No se recibió request")

        issues = []
        sanitized = {}

        # 1. Generar request_id anónimo
        request_id = str(uuid.uuid4())
        sanitized["request_id"] = request_id
        context.set("request_id", request_id)

        # 2. Validar coordenadas dentro de CDMX
        origin = request.origin
        destination = request.destination

        if not validate_cdmx_coordinates(origin.lat, origin.lon):
            issues.append(
                f"Origen fuera de CDMX: ({origin.lat}, {origin.lon})"
            )

        if not validate_cdmx_coordinates(destination.lat, destination.lon):
            issues.append(
                f"Destino fuera de CDMX: ({destination.lat}, {destination.lon})"
            )

        if issues:
            return AgentResult(
                success=False,
                error=f"Validación fallida: {'; '.join(issues)}",
                data={"issues": issues},
            )

        # 3. Truncar coordenadas (minimización de datos)
        sanitized["origin_lat"] = truncate_coordinate(origin.lat)
        sanitized["origin_lon"] = truncate_coordinate(origin.lon)
        sanitized["dest_lat"] = truncate_coordinate(destination.lat)
        sanitized["dest_lon"] = truncate_coordinate(destination.lon)

        # 4. Validar que no haya datos sensibles en campos de texto
        # (Para MVP, los únicos campos de texto son enums, pero preparamos la validación)
        request_str = str(request.model_dump())
        for pattern, data_type in self.SENSITIVE_PATTERNS:
            if pattern.search(request_str):
                issues.append(f"Posible dato sensible detectado: {data_type}")

        if issues:
            self.logger.warning(f"Datos sensibles detectados: {issues}")

        # 5. Log de auditoría (sin datos personales)
        self.logger.info(
            f"[{request_id}] Request validado. "
            f"Origen: ({sanitized['origin_lat']}, {sanitized['origin_lon']}), "
            f"Destino: ({sanitized['dest_lat']}, {sanitized['dest_lon']}), "
            f"Prioridad: {request.priority.value}"
        )

        context.set("sanitized_request", sanitized)

        return AgentResult(
            success=True,
            data={
                "request_id": request_id,
                "sanitized": sanitized,
                "issues": issues,
                "coordinates_truncated": True,
            },
        )
