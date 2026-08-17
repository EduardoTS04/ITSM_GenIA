"""End-to-end tests for the 4 ticket endpoints via httpx.AsyncClient.

The LLM port is replaced by a fake (see the `fake_agent` fixture), so these
tests never reach Ollama. Assertions target status codes and key fields rather
than whole-body snapshots, to keep them robust against cosmetic changes.
"""

import asyncio

import pytest

from app.domain.ports import AgentAnalysisResult
from app.presentation.api.deps import get_llm_agent

from tests.fakes import FakeLLMAgent, default_analysis

TICKET_KEYS = {
    "id", "titulo", "descripcion", "tipo", "categoria", "subcategoria", "prioridad", "estado",
    "area_responsable", "impacto", "urgencia", "razon_clasificacion", "razon_prioridad",
    "confianza_clasificacion", "respuesta_estructurada", "respuesta_usuario", "escalado_a_humano",
    "es_recurrente", "causa_raiz", "accion_preventiva", "creado_en", "actualizado_en",
}


async def create(client, titulo="VPN caída", descripcion="No puedo acceder al ERP"):
    response = await client.post("/api/v1/tickets", json={"titulo": titulo, "descripcion": descripcion})
    assert response.status_code == 201, response.text
    return response.json()


# ── POST /tickets ──────────────────────────────────────────────────────────────

async def test_create_returns_201_with_the_agent_analysis(async_client, fake_agent):
    body = await create(async_client)

    assert isinstance(body["id"], int)
    assert body["titulo"] == "VPN caída"
    assert body["tipo"] == "incidente"
    assert body["categoria"] == "Red"
    assert body["prioridad"] == "P1"
    assert body["estado"] == "nuevo"
    assert body["area_responsable"] == "Infraestructura"
    assert body["escalado_a_humano"] is False
    assert fake_agent.calls == [("VPN caída", "No puedo acceder al ERP")]


async def test_create_response_exposes_the_documented_fields(async_client):
    body = await create(async_client)

    assert set(body) == TICKET_KEYS


async def test_create_returns_the_structured_answer_and_its_plaintext(async_client):
    body = await create(async_client)

    expected = default_analysis().respuesta_estructurada
    assert body["respuesta_estructurada"] == expected
    assert body["respuesta_usuario"].startswith(expected["saludo"])
    assert "1. Reiniciar el cliente VPN" in body["respuesta_usuario"]


async def test_create_applies_fallbacks_when_the_pipeline_is_degraded(async_client, fake_agent):
    fake_agent.result = AgentAnalysisResult()

    body = await create(async_client, titulo="Sin IA", descripcion="fallback")

    assert body["tipo"] == "incidente"
    assert body["categoria"] == "General"
    assert body["prioridad"] == "P3"
    assert body["respuesta_estructurada"] is None
    assert body["respuesta_usuario"] == "No hay respuesta de soporte disponible."


async def test_a_slow_agent_does_not_block_other_requests(async_client, api_app):
    """The create handler awaits the agent, so the loop stays free meanwhile."""

    class SlowAgent(FakeLLMAgent):
        def __init__(self) -> None:
            super().__init__()
            self.released = asyncio.Event()

        async def analyze(self, titulo: str, descripcion: str):
            await asyncio.wait_for(self.released.wait(), timeout=5)
            return await super().analyze(titulo, descripcion)

    slow_agent = SlowAgent()
    api_app.dependency_overrides[get_llm_agent] = lambda: slow_agent

    create_task = asyncio.create_task(
        async_client.post("/api/v1/tickets", json={"titulo": "Lenta", "descripcion": "d"})
    )
    health = await async_client.get("/health")
    slow_agent.released.set()
    created = await create_task

    assert health.status_code == 200
    assert created.status_code == 201


@pytest.mark.parametrize("payload", [{}, {"titulo": "solo titulo"}, {"descripcion": "sola descripcion"}])
async def test_create_rejects_incomplete_payloads(async_client, payload):
    response = await async_client.post("/api/v1/tickets", json=payload)

    assert response.status_code == 422


# ── GET /tickets ───────────────────────────────────────────────────────────────

async def test_list_is_empty_before_anything_is_created(async_client):
    response = await async_client.get("/api/v1/tickets")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_returns_created_tickets_newest_first(async_client, fake_agent):
    first = await create(async_client, titulo="Primero")
    fake_agent.result = AgentAnalysisResult(tipo="requerimiento", categoria="Hardware", prioridad="P4")
    second = await create(async_client, titulo="Segundo")

    response = await async_client.get("/api/v1/tickets")

    assert response.status_code == 200
    ids = [t["id"] for t in response.json()]
    assert set(ids) == {first["id"], second["id"]}
    assert ids[0] == second["id"]


async def test_list_filters_by_free_text(async_client):
    created = await create(async_client, titulo="VPN caída", descripcion="No puedo acceder al ERP")
    await create(async_client, titulo="Teclado roto", descripcion="Teclas sin respuesta")

    response = await async_client.get("/api/v1/tickets", params={"q": "ERP"})

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [created["id"]]


async def test_list_filters_by_exact_fields(async_client, fake_agent):
    await create(async_client, titulo="Incidente de red")
    fake_agent.result = AgentAnalysisResult(tipo="requerimiento", categoria="Hardware", prioridad="P4",
                                           urgencia="baja", area_responsable="Helpdesk")
    requerimiento = await create(async_client, titulo="Nuevo teclado")

    for params in [{"tipo": "requerimiento"}, {"categoria": "Hardware"},
                   {"prioridad": "P4"}, {"urgencia": "baja"}, {"area_responsable": "Helpdesk"}]:
        response = await async_client.get("/api/v1/tickets", params=params)
        assert response.status_code == 200, params
        assert [t["id"] for t in response.json()] == [requerimiento["id"]], params


async def test_list_ignores_unparseable_dates(async_client):
    await create(async_client)

    response = await async_client.get("/api/v1/tickets", params={"fecha_desde": "not-a-date"})

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_list_date_range_can_exclude_everything(async_client):
    await create(async_client)

    response = await async_client.get("/api/v1/tickets", params={"fecha_hasta": "1900-01-01"})

    assert response.status_code == 200
    assert response.json() == []


# ── GET /tickets/{id} ──────────────────────────────────────────────────────────

async def test_get_returns_the_ticket(async_client):
    created = await create(async_client)

    response = await async_client.get(f"/api/v1/tickets/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["titulo"] == created["titulo"]
    assert set(body) == TICKET_KEYS


async def test_get_unknown_id_returns_404_with_a_message(async_client):
    response = await async_client.get("/api/v1/tickets/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket 999999 no encontrado."


async def test_get_non_numeric_id_is_a_validation_error(async_client):
    response = await async_client.get("/api/v1/tickets/abc")

    assert response.status_code == 422


# ── POST /tickets/{id}/escalate ────────────────────────────────────────────────

async def test_escalate_marks_the_ticket_for_a_human(async_client):
    created = await create(async_client)

    response = await async_client.post(f"/api/v1/tickets/{created['id']}/escalate")

    assert response.status_code == 200
    assert response.json()["escalado_a_humano"] is True


async def test_escalation_is_visible_on_subsequent_reads(async_client):
    created = await create(async_client)

    await async_client.post(f"/api/v1/tickets/{created['id']}/escalate")
    response = await async_client.get(f"/api/v1/tickets/{created['id']}")

    assert response.json()["escalado_a_humano"] is True


async def test_escalate_is_idempotent(async_client):
    created = await create(async_client)

    first = await async_client.post(f"/api/v1/tickets/{created['id']}/escalate")
    second = await async_client.post(f"/api/v1/tickets/{created['id']}/escalate")

    assert first.status_code == second.status_code == 200
    assert second.json()["escalado_a_humano"] is True


async def test_escalate_unknown_id_returns_404(async_client):
    response = await async_client.post("/api/v1/tickets/999999/escalate")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket 999999 no encontrado."
