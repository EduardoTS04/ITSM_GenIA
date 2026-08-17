"""Integration tests for SqlAlchemyTicketRepository against a real SQLite file."""

from datetime import datetime

import pytest

from app.domain.entities.ticket import Ticket
from app.domain.ports import TicketFilters


def make_ticket(**overrides) -> Ticket:
    """A valid ticket; `creado_en` is explicit so date filters are deterministic."""
    fields = {
        "titulo": "VPN caída",
        "descripcion": "No puedo acceder al ERP",
        "tipo": "incidente",
        "categoria": "Red",
        "subcategoria": "VPN",
        "prioridad": "P1",
        "estado": "nuevo",
        "area_responsable": "Infraestructura",
        "impacto": "alto",
        "urgencia": "alta",
        "creado_en": datetime(2026, 3, 10, 9, 0, 0),
        "actualizado_en": datetime(2026, 3, 10, 9, 0, 0),
    }
    fields.update(overrides)
    return Ticket(**fields)


@pytest.fixture
def seeded(ticket_repository):
    """Two tickets that differ in every filterable field."""
    first = ticket_repository.add(make_ticket())
    second = ticket_repository.add(make_ticket(
        titulo="Teclado roto",
        descripcion="Las teclas no responden",
        tipo="requerimiento",
        categoria="Hardware",
        subcategoria=None,
        prioridad="P4",
        area_responsable="Helpdesk",
        impacto="bajo",
        urgencia="baja",
        creado_en=datetime(2026, 5, 20, 18, 30, 0),
        actualizado_en=datetime(2026, 5, 20, 18, 30, 0),
    ))
    return first, second


# ── add / get_by_id ────────────────────────────────────────────────────────────

def test_add_assigns_an_id_and_persists_the_row(ticket_repository, db_session):
    ticket = ticket_repository.add(make_ticket())

    assert ticket.id is not None
    assert db_session.query(Ticket).count() == 1


def test_add_round_trips_every_column(ticket_repository):
    stored = ticket_repository.add(make_ticket(
        razon_clasificacion="razón",
        razon_prioridad="prioridad alta",
        confianza_clasificacion=0.75,
        respuesta_estructurada='{"saludo": "Hola"}',
        es_recurrente=True,
        causa_raiz="certificado",
        accion_preventiva="renovar",
    ))

    found = ticket_repository.get_by_id(stored.id)
    assert found is stored
    assert found.confianza_clasificacion == 0.75
    assert found.respuesta_estructurada == '{"saludo": "Hola"}'
    assert found.es_recurrente is True
    assert found.causa_raiz == "certificado"
    assert found.accion_preventiva == "renovar"


def test_get_by_id_returns_none_when_absent(ticket_repository):
    assert ticket_repository.get_by_id(999_999) is None


# ── update ─────────────────────────────────────────────────────────────────────

def test_update_persists_a_mutation(ticket_repository, db_engine):
    ticket = ticket_repository.add(make_ticket())

    ticket.escalado_a_humano = True
    ticket_repository.update(ticket)

    from sqlalchemy.orm import sessionmaker
    fresh = sessionmaker(bind=db_engine)()
    try:
        reloaded = fresh.query(Ticket).filter(Ticket.id == ticket.id).first()
        assert reloaded.escalado_a_humano is True
    finally:
        fresh.close()


# ── list: no filters and ordering ──────────────────────────────────────────────

def test_list_without_filters_returns_everything_newest_first(ticket_repository, seeded):
    first, second = seeded

    rows = ticket_repository.list(TicketFilters())

    assert [t.id for t in rows] == [second.id, first.id]


def test_list_on_an_empty_table_returns_an_empty_list(ticket_repository):
    assert ticket_repository.list(TicketFilters()) == []


# ── list: text search ──────────────────────────────────────────────────────────

def test_q_matches_the_title(ticket_repository, seeded):
    first, _ = seeded

    assert [t.id for t in ticket_repository.list(TicketFilters(q="VPN"))] == [first.id]


def test_q_matches_the_description(ticket_repository, seeded):
    first, _ = seeded

    assert [t.id for t in ticket_repository.list(TicketFilters(q="ERP"))] == [first.id]


def test_q_is_a_substring_match(ticket_repository, seeded):
    _, second = seeded

    assert [t.id for t in ticket_repository.list(TicketFilters(q="eclado"))] == [second.id]


def test_q_without_matches_returns_nothing(ticket_repository, seeded):
    assert ticket_repository.list(TicketFilters(q="zzz")) == []


def test_empty_q_is_treated_as_no_filter(ticket_repository, seeded):
    assert len(ticket_repository.list(TicketFilters(q=""))) == 2


# ── list: exact-match filters ──────────────────────────────────────────────────

@pytest.mark.parametrize("field,value,expect_first", [
    ("tipo", "incidente", True),
    ("tipo", "requerimiento", False),
    ("categoria", "Red", True),
    ("categoria", "Hardware", False),
    ("prioridad", "P1", True),
    ("prioridad", "P4", False),
    ("urgencia", "alta", True),
    ("urgencia", "baja", False),
    ("area_responsable", "Infraestructura", True),
    ("area_responsable", "Helpdesk", False),
])
def test_exact_filters_select_the_right_ticket(ticket_repository, seeded, field, value, expect_first):
    first, second = seeded
    expected = first if expect_first else second

    rows = ticket_repository.list(TicketFilters(**{field: value}))

    assert [t.id for t in rows] == [expected.id]


def test_unknown_filter_value_matches_nothing(ticket_repository, seeded):
    assert ticket_repository.list(TicketFilters(categoria="Inexistente")) == []


def test_filters_combine_with_and(ticket_repository, seeded):
    assert ticket_repository.list(TicketFilters(tipo="incidente", prioridad="P4")) == []


# ── list: date range ───────────────────────────────────────────────────────────

def test_fecha_desde_excludes_older_tickets(ticket_repository, seeded):
    _, second = seeded

    rows = ticket_repository.list(TicketFilters(fecha_desde="2026-04-01"))

    assert [t.id for t in rows] == [second.id]


def test_fecha_hasta_excludes_newer_tickets(ticket_repository, seeded):
    first, _ = seeded

    rows = ticket_repository.list(TicketFilters(fecha_hasta="2026-04-01"))

    assert [t.id for t in rows] == [first.id]


def test_fecha_hasta_includes_the_whole_day(ticket_repository, seeded):
    """The 18:30 ticket must still match when filtering up to its own date."""
    _, second = seeded

    rows = ticket_repository.list(TicketFilters(fecha_desde="2026-05-20", fecha_hasta="2026-05-20"))

    assert [t.id for t in rows] == [second.id]


def test_date_range_spanning_both_tickets(ticket_repository, seeded):
    rows = ticket_repository.list(TicketFilters(fecha_desde="2026-01-01", fecha_hasta="2026-12-31"))

    assert len(rows) == 2


@pytest.mark.parametrize("bad_date", ["not-a-date", "2026-13-45", "10/03/2026", ""])
def test_unparseable_dates_are_ignored_rather_than_failing(ticket_repository, seeded, bad_date):
    assert len(ticket_repository.list(TicketFilters(fecha_desde=bad_date))) == 2
    assert len(ticket_repository.list(TicketFilters(fecha_hasta=bad_date))) == 2
