"""FastAPI dependency providers for the API layer."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.agents.orchestrator import OllamaConfig
from app.application.use_cases.create_ticket import CreateTicketUseCase
from app.core.config import settings
from app.domain.ports import AgentTraceRepository, LLMAgentPort, TicketRepository
from app.infrastructure.database.connection import get_db
from app.infrastructure.db.agent_trace_repository import SqlAlchemyAgentTraceRepository
from app.infrastructure.db.ticket_repository import SqlAlchemyTicketRepository
from app.infrastructure.llm.ollama_orchestrator_adapter import OllamaOrchestratorAdapter


def get_ticket_repository(db: Session = Depends(get_db)) -> TicketRepository:
    """Build a TicketRepository bound to the request-scoped DB session."""
    return SqlAlchemyTicketRepository(db)


def get_agent_trace_repository(db: Session = Depends(get_db)) -> AgentTraceRepository:
    """Build an AgentTraceRepository bound to the request-scoped DB session."""
    return SqlAlchemyAgentTraceRepository(db)


def get_llm_agent() -> LLMAgentPort:
    """Build the GenAI adapter used to analyze incoming tickets."""
    return OllamaOrchestratorAdapter(
        OllamaConfig(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
            max_retries=settings.OLLAMA_MAX_RETRIES,
            backoff_seconds=settings.OLLAMA_RETRY_BACKOFF_SECONDS,
        )
    )


def get_create_ticket_use_case(
    tickets: TicketRepository = Depends(get_ticket_repository),
    agent: LLMAgentPort = Depends(get_llm_agent),
    traces: AgentTraceRepository = Depends(get_agent_trace_repository),
) -> CreateTicketUseCase:
    return CreateTicketUseCase(tickets=tickets, agent=agent, traces=traces)
