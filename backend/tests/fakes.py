"""Test doubles shared by the unit, integration and API suites."""

from typing import Optional, Sequence

from app.domain.entities.agent_trace import AgentTrace
from app.domain.entities.ticket import Ticket
from app.domain.ports import (
    AgentAnalysisResult,
    AgentTraceRecord,
    AgentTraceRepository,
    LLMAgentPort,
    TicketFilters,
    TicketRepository,
)

AGENT_NAMES = ["clasificador", "priorizador", "soporte", "analitico"]


def default_traces() -> list[AgentTraceRecord]:
    """One successful trace per agent, as a healthy pipeline run would produce."""
    return [
        AgentTraceRecord(
            agent_name=name,
            prompt_version="v1",
            input_summary="VPN caída — No puedo acceder al ERP",
            latency_ms=100 + index,
            success=True,
            raw_output='{"ok": true}',
        )
        for index, name in enumerate(AGENT_NAMES)
    ]


def default_analysis() -> AgentAnalysisResult:
    """A fully-populated analysis, as the 4 agents would return on success."""
    return AgentAnalysisResult(
        tipo="incidente",
        categoria="Red",
        subcategoria="VPN",
        confianza_clasificacion=0.92,
        razon_clasificacion="Falla de conectividad VPN.",
        prioridad="P1",
        impacto="alto",
        urgencia="alta",
        area_responsable="Infraestructura",
        razon_prioridad="Bloquea el acceso al ERP.",
        respuesta_estructurada={
            "saludo": "Hola, lamentamos el inconveniente.",
            "pasos_solucion": [
                {"numero": 1, "titulo": "Reiniciar el cliente VPN", "descripcion": "Cierra y abre la aplicación."},
                {"numero": 2, "titulo": "Verificar credenciales", "descripcion": "Confirma tu usuario y contraseña."},
            ],
            "tiempo_estimado": "10-15 minutos",
            "cierre": "Si el problema persiste, escala el ticket.",
        },
        respuesta_usuario="Texto plano derivado; no se persiste.",
        es_recurrente=True,
        causa_raiz="Certificado VPN vencido.",
        accion_preventiva="Renovar certificados trimestralmente.",
        traces=default_traces(),
    )


class FakeLLMAgent(LLMAgentPort):
    """Stand-in for the Ollama adapter. Records calls, returns a canned result."""

    def __init__(self, result: Optional[AgentAnalysisResult] = None) -> None:
        self.result = result if result is not None else default_analysis()
        self.calls: list[tuple[str, str]] = []

    async def analyze(self, titulo: str, descripcion: str) -> AgentAnalysisResult:
        self.calls.append((titulo, descripcion))
        return self.result


class InMemoryTicketRepository(TicketRepository):
    """Minimal repository standing in for the SQLAlchemy implementation."""

    def __init__(self) -> None:
        self.rows: list[Ticket] = []

    def add(self, ticket: Ticket) -> Ticket:
        ticket.id = len(self.rows) + 1
        self.rows.append(ticket)
        return ticket

    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        return next((t for t in self.rows if t.id == ticket_id), None)

    def list(self, filters: TicketFilters) -> list[Ticket]:
        return list(self.rows)

    def update(self, ticket: Ticket) -> Ticket:
        return ticket


class InMemoryAgentTraceRepository(AgentTraceRepository):
    """Trace repository standing in for the SQLAlchemy implementation."""

    def __init__(self) -> None:
        self.rows: list[AgentTrace] = []

    def add_traces(self, ticket_id: int, traces: Sequence[AgentTraceRecord]) -> None:
        for record in traces:
            self.rows.append(AgentTrace(
                id=len(self.rows) + 1,
                ticket_id=ticket_id,
                agent_name=record.agent_name,
                prompt_version=record.prompt_version,
                input_summary=record.input_summary,
                raw_output=record.raw_output,
                latency_ms=record.latency_ms,
                success=record.success,
                error_type=record.error_type,
            ))

    def get_traces_by_ticket_id(self, ticket_id: int) -> list[AgentTrace]:
        return [row for row in self.rows if row.ticket_id == ticket_id]
