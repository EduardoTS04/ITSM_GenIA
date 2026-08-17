"""Create-ticket use case: analyze with the agents, then persist the ticket."""

import json
import logging
from typing import Optional, Sequence

from app.domain.entities.ticket import Ticket
from app.domain.ports import (
    AgentTraceRecord,
    AgentTraceRepository,
    LLMAgentPort,
    TicketRepository,
)

logger = logging.getLogger(__name__)


class CreateTicketUseCase:
    def __init__(self, tickets: TicketRepository, agent: LLMAgentPort,
                 traces: Optional[AgentTraceRepository] = None) -> None:
        self._tickets = tickets
        self._agent = agent
        # Optional: without a trace repository the pipeline simply runs untraced.
        self._traces = traces

    async def execute(self, titulo: str, descripcion: str) -> Ticket:
        analysis = await self._agent.analyze(titulo=titulo, descripcion=descripcion)

        # Serialize structured solution
        resp_est_json = None
        if analysis.respuesta_estructurada is not None:
            resp_est_json = json.dumps(analysis.respuesta_estructurada, ensure_ascii=False)

        ticket = Ticket(
            titulo=titulo,
            descripcion=descripcion,
            tipo=analysis.tipo,
            categoria=analysis.categoria,
            subcategoria=analysis.subcategoria,
            prioridad=analysis.prioridad,
            estado="nuevo",
            area_responsable=analysis.area_responsable,
            impacto=analysis.impacto,
            urgencia=analysis.urgencia,
            razon_clasificacion=analysis.razon_clasificacion,
            razon_prioridad=analysis.razon_prioridad,
            confianza_clasificacion=analysis.confianza_clasificacion,
            respuesta_estructurada=resp_est_json,
            escalado_a_humano=False,
            es_recurrente=bool(analysis.es_recurrente),
            causa_raiz=analysis.causa_raiz,
            accion_preventiva=analysis.accion_preventiva,
        )

        ticket = self._tickets.add(ticket)
        self._record_traces(ticket.id, analysis.traces)
        return ticket

    def _record_traces(self, ticket_id: int, traces: Sequence[AgentTraceRecord]) -> None:
        """Store the pipeline trace. Observability must never break ticket creation."""
        if self._traces is None or not traces:
            return
        try:
            self._traces.add_traces(ticket_id, traces)
        except Exception:  # noqa: BLE001
            logger.exception("Could not persist the agent trace for ticket %s", ticket_id)
