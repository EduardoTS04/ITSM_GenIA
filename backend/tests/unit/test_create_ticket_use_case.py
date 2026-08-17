"""Unit tests for CreateTicketUseCase – no FastAPI, no database, no network."""

import json

import pytest

from app.application.use_cases.create_ticket import CreateTicketUseCase
from app.domain.ports import AgentAnalysisResult

from tests.fakes import (
    FakeLLMAgent,
    InMemoryAgentTraceRepository,
    InMemoryTicketRepository,
    default_analysis,
    default_traces,
)


@pytest.fixture
def repo() -> InMemoryTicketRepository:
    return InMemoryTicketRepository()


@pytest.fixture
def traces() -> InMemoryAgentTraceRepository:
    return InMemoryAgentTraceRepository()


# ── Happy path ─────────────────────────────────────────────────────────────────

async def test_happy_path_maps_every_agent_field(repo: InMemoryTicketRepository):
    agent = FakeLLMAgent(default_analysis())

    ticket = await CreateTicketUseCase(tickets=repo, agent=agent).execute(
        titulo="VPN caída", descripcion="No puedo acceder al ERP"
    )

    assert agent.calls == [("VPN caída", "No puedo acceder al ERP")]
    assert ticket.titulo == "VPN caída"
    assert ticket.descripcion == "No puedo acceder al ERP"
    assert ticket.tipo == "incidente"
    assert ticket.categoria == "Red"
    assert ticket.subcategoria == "VPN"
    assert ticket.prioridad == "P1"
    assert ticket.impacto == "alto"
    assert ticket.urgencia == "alta"
    assert ticket.area_responsable == "Infraestructura"
    assert ticket.confianza_clasificacion == 0.92
    assert ticket.razon_clasificacion == "Falla de conectividad VPN."
    assert ticket.razon_prioridad == "Bloquea el acceso al ERP."
    assert ticket.es_recurrente is True
    assert ticket.causa_raiz == "Certificado VPN vencido."
    assert ticket.accion_preventiva == "Renovar certificados trimestralmente."


async def test_happy_path_persists_through_the_repository(repo: InMemoryTicketRepository):
    ticket = await CreateTicketUseCase(tickets=repo, agent=FakeLLMAgent()).execute(titulo="t", descripcion="d")

    assert repo.rows == [ticket]
    assert ticket.id == 1


async def test_new_tickets_start_as_nuevo_and_unescalated(repo: InMemoryTicketRepository):
    ticket = await CreateTicketUseCase(tickets=repo, agent=FakeLLMAgent()).execute(titulo="t", descripcion="d")

    assert ticket.estado == "nuevo"
    assert ticket.escalado_a_humano is False


async def test_structured_answer_is_stored_as_json_text(repo: InMemoryTicketRepository):
    ticket = await CreateTicketUseCase(tickets=repo, agent=FakeLLMAgent()).execute(titulo="t", descripcion="d")

    stored = json.loads(ticket.respuesta_estructurada)
    assert stored == default_analysis().respuesta_estructurada
    assert len(stored["pasos_solucion"]) == 2


async def test_structured_answer_keeps_non_ascii_unescaped(repo: InMemoryTicketRepository):
    agent = FakeLLMAgent(AgentAnalysisResult(respuesta_estructurada={"saludo": "conexión"}))

    ticket = await CreateTicketUseCase(tickets=repo, agent=agent).execute(titulo="t", descripcion="d")

    assert "conexión" in ticket.respuesta_estructurada


async def test_respuesta_usuario_is_never_written_to_the_entity(repo: InMemoryTicketRepository):
    """It is derived on read by the router, so the ORM has no such column."""
    ticket = await CreateTicketUseCase(tickets=repo, agent=FakeLLMAgent()).execute(titulo="t", descripcion="d")

    assert not hasattr(type(ticket), "respuesta_usuario")


# ── Degraded path (Ollama unreachable → orchestrator fallbacks) ─────────────────

async def test_degraded_path_uses_fallback_classification(repo: InMemoryTicketRepository):
    """With every agent failing, the adapter yields an all-defaults analysis."""
    agent = FakeLLMAgent(AgentAnalysisResult())

    ticket = await CreateTicketUseCase(tickets=repo, agent=agent).execute(titulo="Sin IA", descripcion="fallback")

    assert ticket.tipo == "incidente"
    assert ticket.categoria == "General"
    assert ticket.prioridad == "P3"
    assert ticket.estado == "nuevo"
    assert ticket.es_recurrente is False
    assert ticket.causa_raiz is None
    assert ticket.accion_preventiva is None


async def test_degraded_path_leaves_structured_answer_null(repo: InMemoryTicketRepository):
    agent = FakeLLMAgent(AgentAnalysisResult())

    ticket = await CreateTicketUseCase(tickets=repo, agent=agent).execute(titulo="t", descripcion="d")

    assert ticket.respuesta_estructurada is None
    # NOTE: once G11 lands, also assert here that the ticket is flagged degraded.


async def test_degraded_path_still_persists_the_ticket(repo: InMemoryTicketRepository):
    use_case = CreateTicketUseCase(tickets=repo, agent=FakeLLMAgent(AgentAnalysisResult()))

    ticket = await use_case.execute(titulo="t", descripcion="d")

    assert repo.rows == [ticket]


# ── Execution trace (G15) ──────────────────────────────────────────────────────

async def test_traces_are_persisted_against_the_new_ticket(repo, traces):
    use_case = CreateTicketUseCase(tickets=repo, agent=FakeLLMAgent(), traces=traces)

    ticket = await use_case.execute(titulo="t", descripcion="d")

    assert [row.agent_name for row in traces.rows] == ["clasificador", "priorizador", "soporte", "analitico"]
    assert all(row.ticket_id == ticket.id for row in traces.rows)
    assert all(row.latency_ms > 0 for row in traces.rows)


async def test_trace_fields_survive_the_round_trip(repo, traces):
    use_case = CreateTicketUseCase(tickets=repo, agent=FakeLLMAgent(), traces=traces)

    await use_case.execute(titulo="t", descripcion="d")

    expected = default_traces()[0]
    stored = traces.rows[0]
    assert stored.prompt_version == expected.prompt_version
    assert stored.input_summary == expected.input_summary
    assert stored.raw_output == expected.raw_output
    assert stored.success is True
    assert stored.error_type is None


async def test_tracing_is_skipped_when_no_trace_repository_is_wired(repo):
    """The trace repository is optional; without it creation just runs untraced."""
    ticket = await CreateTicketUseCase(tickets=repo, agent=FakeLLMAgent()).execute(titulo="t", descripcion="d")

    assert repo.rows == [ticket]


async def test_an_analysis_without_traces_writes_nothing(repo, traces):
    agent = FakeLLMAgent(AgentAnalysisResult())

    await CreateTicketUseCase(tickets=repo, agent=agent, traces=traces).execute(titulo="t", descripcion="d")

    assert traces.rows == []


async def test_a_failing_trace_write_does_not_fail_ticket_creation(repo, traces, caplog):
    """Observability is best-effort: a broken trace store must not lose the ticket."""

    class BrokenTraceRepository(InMemoryAgentTraceRepository):
        def add_traces(self, ticket_id, traces):
            raise RuntimeError("trace store unavailable")

    use_case = CreateTicketUseCase(tickets=repo, agent=FakeLLMAgent(), traces=BrokenTraceRepository())

    ticket = await use_case.execute(titulo="t", descripcion="d")

    assert repo.rows == [ticket]
    assert ticket.id == 1
    assert "Could not persist the agent trace" in caplog.text


async def test_agent_crash_is_not_swallowed(repo: InMemoryTicketRepository):
    """A crashing port must surface rather than persist a half-built ticket."""

    class ExplodingAgent(FakeLLMAgent):
        async def analyze(self, titulo: str, descripcion: str):
            raise RuntimeError("adapter blew up")

    with pytest.raises(RuntimeError):
        await CreateTicketUseCase(tickets=repo, agent=ExplodingAgent()).execute(titulo="t", descripcion="d")

    assert repo.rows == []
