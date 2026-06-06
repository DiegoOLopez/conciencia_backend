# ConciencIA Backend API

## Descripción General

API REST de movilidad urbana segura para la Ciudad de México (CDMX). El sistema proporciona rutas optimizadas considerando tiempo, seguridad y accesibilidad mediante un sistema multi-agente impulsado por inteligencia artificial.

## Tabla de Contenidos

- [Características Principales](#características-principales)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Requisitos del Sistema](#requisitos-del-sistema)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Documentación de la API](#documentación-de-la-api)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Despliegue](#despliegue)
- [Pruebas](#pruebas)
- [Mantenimiento](#mantenimiento)
- [Contribución](#contribución)
- [Licencia](#licencia)

## Características Principales

### Sistema Multi-Agente

El backend implementa un pipeline de seis agentes especializados:

1. **Agente Orquestador**: Coordina el flujo completo del pipeline de procesamiento
2. **Agente de Privacidad**: Valida y sanitiza las solicitudes entrantes
3. **Agente de Datos Urbanos**: Recopila rutas candidatas y datos de transporte de CDMX
4. **Agente de Evaluación de Riesgo**: Calcula scores de seguridad para cada segmento
5. **Agente Optimizador**: Selecciona las tres mejores rutas según criterios del usuario
6. **Agente Explicador**: Genera explicaciones en lenguaje natural mediante IA

### Funcionalidades Clave

- Optimización inteligente balanceando tiempo, seguridad y accesibilidad
- Integración con datos abiertos de la Ciudad de México
- Soporte para múltiples modos de transporte (caminar, bicicleta, Metro, Metrobús, RTP, Tren Ligero)
- Generación de explicaciones mediante Google Gemini
- Sistema de rate limiting configurable
- Configuración flexible de CORS

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  POST /api/v1/routes  │  GET /health  │  Middlewares        │
├─────────────────────────────────────────────────────────────┤
│                    Agent Pipeline                            │
│  1. Privacy → 2. Urban Data → 3. Risk → 4. Optimizer        │
│                    → 5. Explainer                            │
├─────────────────────────────────────────────────────────────┤
│                   External Services                          │
│  • OSRM (Routing)  • Google Gemini  • CDMX Open Data       │
└─────────────────────────────────────────────────────────────┘
```

### Flujo del Pipeline de Agentes

1. **Privacy Agent**: Valida que las coordenadas estén dentro de los límites de CDMX y sanitiza los datos de entrada
2. **Urban Data Agent**: Obtiene rutas candidatas del servicio OSRM y recopila datos de transporte público
3. **Risk Agent**: Calcula scores de riesgo basados en hora del día, modo de transporte y ubicación geográfica
4. **Optimizer Agent**: Selecciona las tres mejores rutas según la prioridad especificada por el usuario
5. **Explainer Agent**: Genera explicaciones y resúmenes en lenguaje natural utilizando Google Gemini

## Requisitos del Sistema

### Software Requerido

- Python 3.12 o superior
- pip (gestor de paquetes de Python)
- Conexión a Internet (para servicios externos)

### Servicios Externos

- Google Gemini API Key (opcional para MVP, requerido para explicaciones con IA)
- Acceso a OSRM (servidor público por defecto)
- Acceso a datos abiertos de CDMX

## Instalación

### Paso 1: Clonar el Repositorio

```bash
git clone <repository-url>
cd backend
```

### Paso 2: Crear Entorno Virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### Paso 3: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Configurar Variables de Entorno

Copiar el archivo de ejemplo y configurar los valores necesarios:

```bash
cp .env.example .env
```

Editar el archivo `.env` con la configuración apropiada:

```env
# Google Gemini (opcional para MVP)
GEMINI_API_KEY=su_api_key_aqui
GEMINI_MODEL=gemini-2.0-flash

# OSRM (servidor público por defecto)
OSRM_BASE_URL=https://router.project-osrm.org

# CORS
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# Rate limiting
RATE_LIMIT_PER_MINUTE=30

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

## Configuración

### Variables de Entorno

| Variable | Descripción | Valor por Defecto | Requerido |
|----------|-------------|-------------------|-----------|
| `GEMINI_API_KEY` | Clave de API de Google Gemini | - | No* |
| `GEMINI_MODEL` | Modelo de Gemini a utilizar | `gemini-2.0-flash` | No |
| `OSRM_BASE_URL` | URL base del servicio OSRM | `https://router.project-osrm.org` | No |
| `ALLOWED_ORIGINS` | Orígenes permitidos para CORS | `["http://localhost:3000"]` | No |
| `RATE_LIMIT_PER_MINUTE` | Límite de solicitudes por minuto | `30` | No |
| `LOG_LEVEL` | Nivel de logging | `INFO` | No |
| `DEBUG` | Modo de depuración | `false` | No |

*Requerido para funcionalidad completa con explicaciones de IA

### Límites Geográficos

El sistema valida que las coordenadas estén dentro de los límites de CDMX:

- Latitud: 19.0° - 19.6°
- Longitud: -99.5° - -98.9°

## Uso

### Ejecución en Desarrollo

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://localhost:8000`

### Documentación Interactiva

Una vez iniciado el servidor, la documentación interactiva está disponible en:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Verificación de Estado

```bash
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "service": "ConciencIA API",
  "version": "0.1.0"
}
```

## Documentación de la API

### Endpoint Principal: Cálculo de Rutas

**POST** `/api/v1/routes`

Calcula las tres mejores rutas entre un origen y destino especificados.

#### Solicitud

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "origin": {
    "lat": 19.4326,
    "lon": -99.1332
  },
  "destination": {
    "lat": 19.4285,
    "lon": -99.1677
  },
  "departure_time": "2026-06-06T08:00:00",
  "transport_modes": ["WALK", "METRO", "METROBUS"],
  "priority": "BALANCED"
}
```

#### Parámetros

| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|-----------|
| `origin` | Object | Coordenadas de origen | Sí |
| `origin.lat` | Float | Latitud (19.0-19.6) | Sí |
| `origin.lon` | Float | Longitud (-99.5--98.9) | Sí |
| `destination` | Object | Coordenadas de destino | Sí |
| `destination.lat` | Float | Latitud (19.0-19.6) | Sí |
| `destination.lon` | Float | Longitud (-99.5--98.9) | Sí |
| `departure_time` | String | Hora de salida (ISO 8601) | Sí |
| `transport_modes` | Array | Modos de transporte permitidos | Sí |
| `priority` | String | Prioridad de optimización | Sí |

#### Modos de Transporte Disponibles

- `WALK`: Caminar
- `BIKE`: Bicicleta
- `METRO`: Metro
- `METROBUS`: Metrobús
- `RTP`: Red de Transporte de Pasajeros
- `LIGHT_RAIL`: Tren Ligero
- `TROLLEYBUS`: Trolebús
- `BUS`: Autobús
- `CAR`: Automóvil

#### Prioridades de Optimización

- `SPEED`: Optimizar por velocidad
- `SAFETY`: Optimizar por seguridad
- `BALANCED`: Balance entre velocidad y seguridad (recomendado)

#### Respuesta Exitosa (200 OK)

```json
{
  "routes": [
    {
      "rank": 1,
      "segments": [
        {
          "mode": "WALK",
          "polyline": [[19.4326, -99.1332], [19.4330, -99.1340]],
          "distance_km": 0.5,
          "duration_minutes": 6,
          "risk_score": 15.0,
          "description": "Caminar por Av. Insurgentes Sur",
          "transit_line": null,
          "transit_stops": null
        }
      ],
      "total_time_minutes": 25.0,
      "total_distance_km": 3.2,
      "risk_score": 22.5,
      "accessibility_score": 85.0,
      "explanation": "Esta ruta combina Metro Línea 1 con una breve caminata...",
      "summary": "Metro + 5 min caminata — ruta más rápida",
      "transport_modes_used": ["WALK", "METRO"],
      "tags": ["Más rápida", "Accesible"]
    }
  ],
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "computed_at": "2026-06-06T08:00:00Z",
  "computation_time_ms": 1250.5
}
```

#### Respuestas de Error

| Código | Descripción |
|--------|-------------|
| 400 | Solicitud inválida (coordenadas fuera de CDMX, parámetros incorrectos) |
| 429 | Límite de solicitudes excedido |
| 500 | Error interno del servidor |

## Estructura del Proyecto

```
backend/
├── main.py                 # Punto de entrada de FastAPI
├── requirements.txt        # Dependencias de Python
├── Dockerfile             # Configuración de Docker
├── railway.toml           # Configuración de Railway
├── .env.example           # Plantilla de variables de entorno
│
├── api/                   # Capa de API
│   └── v1/
│       ├── router.py      # Router principal de la API
│       └── routes.py      # Definición de endpoints
│
├── agents/                # Sistema multi-agente
│   ├── base.py           # Clase base abstracta para agentes
│   ├── orchestrator.py   # Agente coordinador del pipeline
│   ├── privacy.py        # Agente de validación y privacidad
│   ├── urban_data.py     # Agente de recopilación de datos
│   ├── risk.py           # Agente de evaluación de riesgo
│   ├── optimizer.py      # Agente de optimización de rutas
│   └── explainer.py      # Agente de generación de explicaciones
│
├── core/                  # Configuración central
│   ├── config.py         # Configuración con Pydantic Settings
│   └── security.py       # Middleware de seguridad y rate limiting
│
├── schemas/               # Modelos de datos Pydantic
│   ├── request.py        # Esquemas de solicitud
│   └── response.py       # Esquemas de respuesta
│
├── services/              # Servicios externos
│   ├── gemini_service.py # Cliente de Google Gemini
│   ├── osm_service.py    # Cliente de OSRM
│   ├── cdmx_data_service.py  # Servicio de datos abiertos CDMX
│   ├── gtfs_service.py   # Servicio de datos GTFS
│   └── tlalpan_transit_service.py  # Servicio de datos de Tlalpan
│
├── data/                  # Datos estáticos
│   └── tlalpan_transit.json  # Datos de rutas RTP Tlalpan
│
├── analytics/             # Módulo de análisis de datos
│   ├── analytics_motor.py
│   └── Data/             # Conjuntos de datos de CDMX
│
└── tests/                 # Suite de pruebas
    └── __init__.py
```

## Despliegue

### Despliegue con Docker

#### Construcción de la Imagen

```bash
docker build -t conciencia-backend .
```

#### Ejecución del Contenedor

```bash
docker run -p 8000:8000 --env-file .env conciencia-backend
```

### Despliegue en Railway

El proyecto incluye configuración para despliegue automático en Railway mediante el archivo `railway.toml`:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

#### Variables de Entorno en Railway

Configurar las siguientes variables en el panel de Railway:

- `GEMINI_API_KEY`
- `ALLOWED_ORIGINS` (incluir el dominio de Railway)
- `RATE_LIMIT_PER_MINUTE`
- `LOG_LEVEL`

### Consideraciones para Producción

1. **Servidor OSRM Dedicado**: Considerar implementar un servidor OSRM propio para mejor rendimiento y control
2. **Configuración de CORS**: Especificar dominios exactos en lugar de wildcards
3. **Rate Limiting**: Ajustar límites según la carga esperada
4. **Logging**: Configurar nivel apropiado (INFO o WARNING en producción)
5. **Monitoreo**: Implementar health checks y alertas
6. **Timeouts**: Configurar timeouts apropiados en el proxy reverso
7. **Escalabilidad**: Considerar múltiples instancias con balanceo de carga

## Pruebas

### Ejecución de Pruebas Unitarias

```bash
pytest
```

### Ejecución con Cobertura

```bash
pytest --cov=. --cov-report=html
```

### Ejecución de Pruebas Específicas

```bash
pytest tests/test_agents.py -v
```

## Mantenimiento

### Monitoreo y Logging

El sistema implementa logging estructurado con los siguientes niveles:

- **INFO**: Operaciones normales y eventos importantes
- **WARNING**: Situaciones anómalas que no impiden el funcionamiento
- **ERROR**: Errores que requieren atención

Formato de logs:

```
2026-06-06 08:00:00 | INFO     | conciencia | 🚀 ConciencIA API iniciando...
2026-06-06 08:00:15 | INFO     | routes | Nuevo request: 19.4326,-99.1332 → 19.4285,-99.1677
2026-06-06 08:00:16 | INFO     | routes | Respuesta generada: 3 rutas en 1250ms
```

### Health Check

El endpoint `/health` proporciona información sobre el estado del servicio:

```json
{
  "status": "ok",
  "service": "ConciencIA API",
  "version": "0.1.0"
}
```

### Actualización de Dependencias

```bash
pip install --upgrade -r requirements.txt
```

### Resolución de Problemas Comunes

#### Error de Conexión con Servicios Externos

Verificar:
- Conectividad a Internet
- Configuración de firewall
- URLs de servicios externos en `.env`

#### Error de API Key de Gemini

Verificar:
- Validez de la API key
- Cuotas disponibles en Google Cloud
- Configuración correcta en `.env`

#### Límite de Rate Excedido

Ajustar `RATE_LIMIT_PER_MINUTE` en `.env` según necesidades

## Contribución

### Proceso de Contribución

1. Fork del repositorio
2. Crear branch de feature: `git checkout -b feature/nueva-funcionalidad`
3. Realizar cambios y commits: `git commit -am 'Descripción del cambio'`
4. Push al branch: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

### Estándares de Código

- Seguir PEP 8 para estilo de código Python
- Documentar funciones y clases con docstrings
- Mantener cobertura de pruebas superior al 80%
- Actualizar documentación según cambios realizados

## Licencia

Este proyecto es parte de un hackathon y está disponible para fines educativos y de investigación.

## Referencias

- [Documentación de FastAPI](https://fastapi.tiangolo.com/)
- [Google Gemini API](https://ai.google.dev/)
- [Documentación de OSRM](http://project-osrm.org/)
- [Datos Abiertos CDMX](https://datos.cdmx.gob.mx/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## Contacto y Soporte

Para reportar problemas o solicitar asistencia:

1. Revisar la documentación interactiva en `/docs`
2. Verificar los logs del servidor
3. Comprobar la configuración de variables de entorno
4. Validar conectividad con servicios externos