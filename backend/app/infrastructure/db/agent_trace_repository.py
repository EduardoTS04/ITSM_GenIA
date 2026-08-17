"""SQLAlchemy implementation of the AgentTraceRepository port."""

from typing import Sequence

from sqlalchemy.orm import Session

from app.domain.entities.agent_trace import AgentTrace
from app.domain.ports import AgentTraceRecord, AgentTraceRepository


class SqlAlchemyAgentTraceRepository(AgentTraceRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add_traces(self, ticket_id: int, traces: Sequence[AgentTraceRecord]) -> None:
        self._db.add_all([
            AgentTrace(
                ticket_id=ticket_id,
                agent_name=record.agent_name,
                prompt_version=record.prompt_version,
                input_summary=record.input_summary,
                raw_output=record.raw_output,
                latency_ms=record.latency_ms,
                success=record.success,
                error_type=record.error_type,
            )
            for record in traces
        ])
        self._db.commit()

    def get_traces_by_ticket_id(self, ticket_id: int) -> list[AgentTrace]:
        return (
            self._db.query(AgentTrace)
            .filter(AgentTrace.ticket_id == ticket_id)
            # id breaks ties: agents within one pipeline run can share a timestamp.
            .order_by(AgentTrace.created_at.asc(), AgentTrace.id.asc())
            .all()
        )
