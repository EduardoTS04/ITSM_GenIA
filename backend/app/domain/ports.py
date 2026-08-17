"""Domain ports – abstractions the application depends on, free of framework code."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from app.domain.entities.agent_trace import AgentTrace
from app.domain.entities.ticket import Ticket


@dataclass
class TicketFilters:
    """Criteria for listing tickets. All fields optional; None means "no filter"."""

    q: Optional[str] = None
    fecha_desde: Optional[str] = None
    fecha_hasta: Optional[str] = None
    urgencia: Optional[str] = None
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    prioridad: Optional[str] = None
    area_responsable: Optional[str] = None


class TicketRepository(ABC):
    """Persistence port for the Ticket aggregate."""

    @abstractmethod
    def add(self, ticket: Ticket) -> Ticket:
        """Persist a new ticket and return it with generated fields populated."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Return the ticket with the given id, or None if it does not exist."""
        raise NotImplementedError

    @abstractmethod
    def list(self, filters: TicketFilters) -> list[Ticket]:
        """Return tickets matching the filters, newest first."""
        raise NotImplementedError

    @abstractmethod
    def update(self, ticket: Ticket) -> Ticket:
        """Persist changes made to an already-tracked ticket and return it."""
        raise NotImplementedError


@dataclass(frozen=True)
class AgentTraceRecord:
    """What one agent call is worth remembering: outcome, cost and raw answer."""

    agent_name: str
    prompt_version: str
    input_summary: str
    latency_ms: int
    success: bool
    raw_output: Optional[str] = None
    error_type: Optional[str] = None


class AgentTraceRepository(ABC):
    """Persistence port for the execution trace of a ticket's agent pipeline."""

    @abstractmethod
    def add_traces(self, ticket_id: int, traces: Sequence[AgentTraceRecord]) -> None:
        """Persist the trace of every agent call made for the given ticket."""
        raise NotImplementedError

    @abstractmethod
    def get_traces_by_ticket_id(self, ticket_id: int) -> list[AgentTrace]:
        """Return the ticket's traces in the order they were produced."""
        raise NotImplementedError


@dataclass
class AgentAnalysisResult:
    """Typed mirror of the dict returned by the multi-agent pipeline.

    Defaults match the fallbacks previously applied when a field was absent.
    """

    tipo: str = "incidente"
    categoria: str = "General"
    subcategoria: Optional[str] = None
    confianza_clasificacion: Optional[float] = None
    razon_clasificacion: Optional[str] = None
    prioridad: str = "P3"
    impacto: Optional[str] = None
    urgencia: Optional[str] = None
    area_responsable: Optional[str] = None
    razon_prioridad: Optional[str] = None
    respuesta_estructurada: Optional[dict[str, Any]] = None
    # Plaintext rendering of the support answer; derived on read, never persisted.
    respuesta_usuario: Optional[str] = None
    es_recurrente: bool = False
    causa_raiz: Optional[str] = None
    accion_preventiva: Optional[str] = None
    # One record per agent call behind this analysis; empty when tracing is unavailable.
    traces: list[AgentTraceRecord] = field(default_factory=list)


class LLMAgentPort(ABC):
    """Port for the GenAI analysis of a raw ticket."""

    @abstractmethod
    async def analyze(self, titulo: str, descripcion: str) -> AgentAnalysisResult:
        """Classify, prioritize and draft a support answer for the given ticket."""
        raise NotImplementedError
