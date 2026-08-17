"""
Orchestrator – coordinates the 4 GenAI agents using Ollama (local LLM).
Each agent is a standalone function; the orchestrator calls them in sequence,
building up context at each step.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from app.domain.ports import AgentTraceRecord

logger = logging.getLogger(__name__)

# Bump when a system prompt below changes, so old traces stay interpretable.
PROMPT_VERSION = "v1"

# Traces keep only a truncated view of the ticket, never the whole description.
INPUT_SUMMARY_MAX_LEN = 200


def summarize_input(titulo: str, descripcion: str) -> str:
    """Short, length-capped view of the ticket input, safe to store in a trace."""
    summary = f"{titulo} — {descripcion}"
    if len(summary) <= INPUT_SUMMARY_MAX_LEN:
        return summary
    return summary[: INPUT_SUMMARY_MAX_LEN - 1].rstrip() + "…"


@dataclass(frozen=True)
class PipelineRun:
    """Result of a full pipeline run: the merged analysis plus one trace per agent."""

    analysis: dict
    traces: list[AgentTraceRecord]


@dataclass(frozen=True)
class OllamaConfig:
    """Everything the pipeline needs to talk to Ollama.

    All fields are required on purpose: app/core/config.py is the single source
    of the defaults, and the caller injects them (see the LLM adapter).
    """

    base_url: str
    model: str
    timeout_seconds: float
    max_retries: int
    backoff_seconds: float


# ── Ollama helper ──────────────────────────────────────────────────────────────

async def call_ollama(client: httpx.AsyncClient, system_prompt: str, user_content: str,
                      config: OllamaConfig, agent_name: str,
                      input_summary: str) -> tuple[dict, AgentTraceRecord]:
    """
    Call the Ollama instance at config.base_url via /api/chat and return the parsed
    JSON together with a trace of the call. The dict is empty on any error, so the
    pipeline never crashes.

    Connection errors and timeouts are retried with exponential backoff; any HTTP
    error status fails fast, since retrying a rejected request cannot help. The
    trace covers the whole call, retries included.
    """
    url = f"{config.base_url}/api/chat"

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
        "stream": False,
        "format": "json",
    }

    started = time.perf_counter()
    data: dict = {}
    raw_output: Optional[str] = None
    error_type: Optional[str] = None

    attempts = max(1, config.max_retries + 1)
    for attempt in range(attempts):
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            content = response.json()["message"]["content"]
            raw_output = content if isinstance(content, str) else repr(content)
            data = json.loads(content)
            error_type = None
            break
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            error_type = exc.__class__.__name__
            remaining = attempts - attempt - 1
            if remaining:
                delay = config.backoff_seconds * (2 ** attempt)
                logger.warning(
                    "Ollama call to %s failed (%s); retrying in %.1f s (%d attempt(s) left).",
                    url, error_type, delay, remaining,
                )
                await asyncio.sleep(delay)
                continue
            logger.error("Ollama unreachable at %s after %d attempt(s): %s", url, attempts, exc)
            break
        except httpx.HTTPStatusError as exc:
            error_type = exc.__class__.__name__
            logger.error("Ollama returned HTTP %s for %s", exc.response.status_code, url)
            break
        except (KeyError, json.JSONDecodeError) as exc:
            error_type = exc.__class__.__name__
            logger.error("Failed to parse Ollama response: %s", exc)
            break
        except Exception as exc:  # noqa: BLE001
            error_type = exc.__class__.__name__
            logger.error("Unexpected error calling Ollama: %s", exc)
            break

    trace = AgentTraceRecord(
        agent_name=agent_name,
        prompt_version=PROMPT_VERSION,
        input_summary=input_summary,
        # A sub-millisecond call still counts as 1 ms, so consumers can rely on > 0.
        latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
        success=error_type is None,
        raw_output=raw_output,
        error_type=error_type,
    )
    return data, trace


# ── Agent 1 – Clasificador ─────────────────────────────────────────────────────

CLASIFICADOR_SYSTEM = (
    "Eres un agente ITSM clasificador. Analiza el ticket y responde ÚNICAMENTE "
    "en JSON válido con estos campos exactos:\n"
    '{"tipo": "incidente|requerimiento|problema", '
    '"categoria": "string (ej: Red, Hardware, Software, Accesos)", '
    '"subcategoria": "string o null", '
    '"confianza": número entre 0.0 y 1.0, '
    '"razon": "explicación breve en español"}'
)

async def agente_clasificador(titulo: str, descripcion: str, client: httpx.AsyncClient,
                              config: OllamaConfig) -> tuple[dict, AgentTraceRecord]:
    """Agent 1: Classify ticket type, category and confidence."""
    user_content = f"Título: {titulo}\nDescripción: {descripcion}"
    result, trace = await call_ollama(
        client, CLASIFICADOR_SYSTEM, user_content, config,
        "clasificador", summarize_input(titulo, descripcion),
    )

    # Safe defaults so the system never breaks
    return {
        "tipo":         result.get("tipo", "incidente"),
        "categoria":    result.get("categoria", "General"),
        "subcategoria": result.get("subcategoria"),
        "confianza":    float(result.get("confianza", 0.5)),
        "razon_clasificacion": result.get("razon", "Clasificación automática por defecto."),
    }, trace


# ── Agent 2 – Priorizador ──────────────────────────────────────────────────────

PRIORIZADOR_SYSTEM = (
    "Eres un agente ITSM de priorización. Analiza el ticket y su clasificación "
    "y responde ÚNICAMENTE en JSON válido con estos campos exactos:\n"
    '{"prioridad": "P1|P2|P3|P4", '
    '"impacto": "alto|medio|bajo", '
    '"urgencia": "alta|media|baja", '
    '"area_responsable": "string (ej: Infraestructura, Helpdesk, Seguridad)", '
    '"razon": "explicación breve en español"}\n'
    "P1=crítico/producción caída, P2=alto impacto, P3=medio, P4=bajo"
)

async def agente_priorizador(titulo: str, descripcion: str, clasificacion: dict,
                             client: httpx.AsyncClient,
                             config: OllamaConfig) -> tuple[dict, AgentTraceRecord]:
    """Agent 2: Assign priority, impact, urgency and responsible team."""
    user_content = (
        f"Título: {titulo}\n"
        f"Descripción: {descripcion}\n"
        f"Clasificación previa: {json.dumps(clasificacion, ensure_ascii=False)}"
    )
    result, trace = await call_ollama(
        client, PRIORIZADOR_SYSTEM, user_content, config,
        "priorizador", summarize_input(titulo, descripcion),
    )

    return {
        "prioridad":        result.get("prioridad", "P3"),
        "impacto":          result.get("impacto", "medio"),
        "urgencia":         result.get("urgencia", "media"),
        "area_responsable": result.get("area_responsable", "Helpdesk"),
        "razon_prioridad":  result.get("razon", "Priorización automática por defecto."),
    }, trace


# ── Agent 3 – Soporte ──────────────────────────────────────────────────────────

SOPORTE_SYSTEM = (
    "Eres un agente de soporte TI. Genera una respuesta empática y clara para "
    "el usuario final con pasos de solución detallados. Responde ÚNICAMENTE en "
    "JSON válido con este esquema exacto:\n"
    "{\n"
    '  "saludo": "un saludo breve y empático al usuario (ej: Hola, lamento que tengas este problema...)",\n'
    '  "pasos_solucion": [\n'
    '    { "numero": 1, "titulo": "título corto del paso", "descripcion": "explicación detallada de lo que debe hacer" }\n'
    '  ],\n'
    '  "tiempo_estimado": "tiempo estimado total (ej: 15-20 minutos)",\n'
    '  "cierre": "mensaje de cierre ofreciendo ayuda adicional si no funciona"\n'
    "}"
)

async def agente_soporte(titulo: str, descripcion: str, clasificacion: dict, priorizacion: dict,
                         client: httpx.AsyncClient,
                         config: OllamaConfig) -> tuple[dict, AgentTraceRecord]:
    """Agent 3: Generate a structured user-facing support response with solution steps."""
    user_content = (
        f"Título: {titulo}\n"
        f"Descripción: {descripcion}\n"
        f"Clasificación: {json.dumps(clasificacion, ensure_ascii=False)}\n"
        f"Priorización: {json.dumps(priorizacion, ensure_ascii=False)}"
    )
    result, trace = await call_ollama(
        client, SOPORTE_SYSTEM, user_content, config,
        "soporte", summarize_input(titulo, descripcion),
    )

    # Safe defaults
    default_steps = [
        {
            "numero": 1,
            "titulo": "Revisar conexión y estado",
            "descripcion": "Comprueba que la conexión de red esté activa y que no haya cortes locales."
        },
        {
            "numero": 2,
            "titulo": "Esperar contacto de soporte",
            "descripcion": "Un agente técnico de nuestro equipo revisará tu caso para brindarte asistencia directa."
        }
    ]

    # Validate output structure
    saludo = result.get("saludo")
    pasos = result.get("pasos_solucion")
    tiempo = result.get("tiempo_estimado")
    cierre = result.get("cierre")

    # If result was text or missing fields, try to construct fallback
    if not saludo or not pasos or not isinstance(pasos, list):
        # Maybe the LLM returned under old schema or text
        old_resp = result.get("respuesta_usuario")
        if old_resp:
            saludo = "Hemos recibido tu reporte."
            pasos = [{"numero": 1, "titulo": "Instrucción de soporte", "descripcion": old_resp}]
            tiempo = "Variable"
            cierre = "Si tienes más problemas, contáctanos."
        else:
            saludo = "Hola. Lamentamos los inconvenientes que estás experimentando con este servicio."
            pasos = default_steps
            tiempo = "15-30 minutos"
            cierre = "Si el problema persiste, puedes escalar este ticket para recibir atención humana."

    return {
        "saludo": saludo,
        "pasos_solucion": pasos,
        "tiempo_estimado": tiempo,
        "cierre": cierre
    }, trace



# ── Agent 4 – Analítico ────────────────────────────────────────────────────────

ANALITICO_SYSTEM = (
    "Eres un agente analítico ITSM. Determina si el ticket parece un incidente "
    "recurrente y sugiere causas raíz o acciones preventivas. Responde ÚNICAMENTE "
    "en JSON válido con estos campos:\n"
    '{"es_recurrente": true|false, '
    '"causa_raiz": "string o null", '
    '"accion_preventiva": "string o null"}'
)

async def agente_analitico(titulo: str, descripcion: str, clasificacion: dict, priorizacion: dict,
                           client: httpx.AsyncClient,
                           config: OllamaConfig) -> tuple[dict, AgentTraceRecord]:
    """Agent 4: Detect recurrence patterns and suggest root cause / prevention."""
    user_content = (
        f"Título: {titulo}\n"
        f"Descripción: {descripcion}\n"
        f"Clasificación: {json.dumps(clasificacion, ensure_ascii=False)}\n"
        f"Priorización: {json.dumps(priorizacion, ensure_ascii=False)}"
    )
    result, trace = await call_ollama(
        client, ANALITICO_SYSTEM, user_content, config,
        "analitico", summarize_input(titulo, descripcion),
    )

    return {
        "es_recurrente":     result.get("es_recurrente", False),
        "causa_raiz":        result.get("causa_raiz"),
        "accion_preventiva": result.get("accion_preventiva"),
    }, trace


# ── Orchestrator ───────────────────────────────────────────────────────────────

async def orchestrate(titulo: str, descripcion: str, config: OllamaConfig,
                      client: httpx.AsyncClient | None = None) -> PipelineRun:
    """
    Main entry point: runs all 4 agents in sequence with accumulated context.
    Returns the unified analysis dict with all fields needed to persist the Ticket
    entity, plus one execution trace per agent call.

    The Ollama connection settings are injected by the caller (see
    app/infrastructure/llm/ollama_orchestrator_adapter.py). Pass `client` to reuse
    an existing AsyncClient; otherwise one is created for this pipeline run.
    """
    if client is None:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as owned_client:
            return await orchestrate(titulo, descripcion, config, owned_client)

    logger.info("Orchestrating agents for ticket: %s", titulo)

    # Agent 1
    clasificacion, traza_clasificador = await agente_clasificador(titulo, descripcion, client, config)
    logger.info("Clasificador result: %s", clasificacion)

    # Agent 2 – receives Agent 1 output as context
    priorizacion, traza_priorizador = await agente_priorizador(titulo, descripcion, clasificacion, client, config)
    logger.info("Priorizador result: %s", priorizacion)

    # Agent 3 – receives Agents 1+2 output as context
    soporte, traza_soporte = await agente_soporte(titulo, descripcion, clasificacion, priorizacion, client, config)
    logger.info("Soporte result: %s", soporte)

    # Agent 4 – receives Agents 1+2 output as context
    analitico, traza_analitico = await agente_analitico(titulo, descripcion, clasificacion, priorizacion, client, config)
    logger.info("Analítico result: %s", analitico)

    # Combine all results into one dict
    analysis = {
        # From Agent 1
        "tipo":                    clasificacion["tipo"],
        "categoria":               clasificacion["categoria"],
        "subcategoria":            clasificacion["subcategoria"],
        "confianza_clasificacion": clasificacion["confianza"],
        "razon_clasificacion":     clasificacion["razon_clasificacion"],
        # From Agent 2
        "prioridad":               priorizacion["prioridad"],
        "impacto":                 priorizacion["impacto"],
        "urgencia":                priorizacion["urgencia"],
        "area_responsable":        priorizacion["area_responsable"],
        "razon_prioridad":         priorizacion["razon_prioridad"],
        # From Agent 3
        "respuesta_estructurada":  soporte,
        "respuesta_usuario":       (
            f"{soporte.get('saludo', '')}\n\n" +
            "\n".join(f"{p.get('numero', i+1)}. {p.get('titulo', '')}: {p.get('descripcion', '')}" for i, p in enumerate(soporte.get('pasos_solucion', []))) +
            f"\n\n{soporte.get('cierre', '')}"
        ),
        # From Agent 4
        "es_recurrente":           analitico["es_recurrente"],
        "causa_raiz":              analitico["causa_raiz"],
        "accion_preventiva":       analitico["accion_preventiva"],
    }

    return PipelineRun(
        analysis=analysis,
        traces=[traza_clasificador, traza_priorizador, traza_soporte, traza_analitico],
    )

