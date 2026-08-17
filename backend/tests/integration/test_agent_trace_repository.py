"""Integration tests for SqlAlchemyAgentTraceRepository against a real SQLite file."""

from datetime import datetime

import pytest

from app.domain.entities.ticket import Ticket
from app.domain.ports import AgentTraceRecord


def make_record(**overrides) -> AgentTraceRecord:
    fields = {
        "agent_name": "clasificador",
        "prompt_version": "v1",
        "input_summary": "VPN caída — No puedo acceder al ERP",
        "latency_ms": 812,
        "success": True,
        "raw_output": '{"tipo": "incidente"}',
        "error_type": None,
    }
    fields.update(overrides)
    return AgentTraceRecord(**fields)


@pytest.fixture
def ticket(ticket_repository) -> Ticket:
    return ticket_repository.add(Ticket(
        titulo="VPN caída",
        descripcion="No puedo acceder al ERP",
        tipo="incidente",
        categoria="Red",
        prioridad="P1",
        estado="nuevo",
        creado_en=datetime(2026, 3, 10, 9, 0, 0),
        actualizado_en=datetime(2026, 3, 10, 9, 0, 0),
    ))


def test_traces_round_trip_every_field(trace_repository, ticket):
    trace_repository.add_traces(ticket.id, [make_record()])

    (stored,) = trace_repository.get_traces_by_ticket_id(ticket.id)
    assert stored.id is not None
    assert stored.ticket_id == ticket.id
    assert stored.agent_name == "clasificador"
    assert stored.prompt_version == "v1"
    assert stored.input_summary == "VPN caída — No puedo acceder al ERP"
    assert stored.raw_output == '{"tipo": "incidente"}'
    assert stored.latency_ms == 812
    assert stored.success is True
    assert stored.error_type is None
    assert stored.created_at is not None


def test_a_whole_pipeline_run_is_stored_in_call_order(trace_repository, ticket):
    names = ["clasificador", "priorizador", "soporte", "analitico"]

    trace_repository.add_traces(ticket.id, [make_record(agent_name=name) for name in names])

    assert [row.agent_name for row in trace_repository.get_traces_by_ticket_id(ticket.id)] == names


def test_failed_calls_keep_their_error_type(trace_repository, ticket):
    trace_repository.add_traces(ticket.id, [
        make_record(agent_name="soporte", success=False, raw_output=None, error_type="ReadTimeout"),
    ])

    (stored,) = trace_repository.get_traces_by_ticket_id(ticket.id)
    assert stored.success is False
    assert stored.raw_output is None
    assert stored.error_type == "ReadTimeout"


def test_traces_are_scoped_to_their_ticket(trace_repository, ticket, ticket_repository):
    other = ticket_repository.add(Ticket(
        titulo="Otro", descripcion="d", tipo="incidente", categoria="General", prioridad="P3", estado="nuevo",
    ))
    trace_repository.add_traces(ticket.id, [make_record()])
    trace_repository.add_traces(other.id, [make_record(agent_name="analitico")])

    assert [row.agent_name for row in trace_repository.get_traces_by_ticket_id(other.id)] == ["analitico"]


def test_a_ticket_without_traces_returns_an_empty_list(trace_repository, ticket):
    assert trace_repository.get_traces_by_ticket_id(ticket.id) == []


def test_an_unknown_ticket_returns_an_empty_list(trace_repository):
    assert trace_repository.get_traces_by_ticket_id(999999) == []


def test_writing_an_empty_run_stores_nothing(trace_repository, ticket):
    trace_repository.add_traces(ticket.id, [])

    assert trace_repository.get_traces_by_ticket_id(ticket.id) == []
