"""End-to-end tests for GET /api/v1/tickets/{id}/trace.

Most tests drive the endpoint through the fake LLM port. The failure test wires the
real Ollama adapter instead and stubs the HTTP calls with respx, so the trace rows
come from a genuine pipeline run rather than from canned records.
"""

import httpx
import respx

from app.agents.orchestrator import OllamaConfig
from app.infrastructure.llm.ollama_orchestrator_adapter import OllamaOrchestratorAdapter
from app.presentation.api.deps import get_agent_trace_repository, get_llm_agent

from tests.fakes import AGENT_NAMES, InMemoryAgentTraceRepository

OLLAMA_URL = "http://ollama.invalid:11434/api/chat"

TRACE_KEYS = {
    "id", "ticket_id", "agent_name", "prompt_version", "input_summary",
    "raw_output", "latency_ms", "success", "error_type", "created_at",
}


async def create(client, titulo="VPN caída", descripcion="No puedo acceder al ERP"):
    response = await client.post("/api/v1/tickets", json={"titulo": titulo, "descripcion": descripcion})
    assert response.status_code == 201, response.text
    return response.json()


def use_real_adapter(api_app, max_retries: int = 0) -> None:
    """Point the app at the real pipeline; respx supplies the HTTP answers."""
    config = OllamaConfig(
        base_url="http://ollama.invalid:11434",
        model="llama3.2",
        timeout_seconds=5.0,
        max_retries=max_retries,
        backoff_seconds=0.0,
    )
    api_app.dependency_overrides[get_llm_agent] = lambda: OllamaOrchestratorAdapter(config)


def agent_reply(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"message": {"content": '{"tipo": "incidente"}'}})


# ── Happy path ─────────────────────────────────────────────────────────────────

async def test_trace_has_one_row_per_agent(async_client):
    created = await create(async_client)

    response = await async_client.get(f"/api/v1/tickets/{created['id']}/trace")

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 4
    assert [row["agent_name"] for row in rows] == AGENT_NAMES
    assert all(row["latency_ms"] > 0 for row in rows)
    assert all(row["success"] is True for row in rows)
    assert all(row["ticket_id"] == created["id"] for row in rows)


async def test_trace_rows_expose_the_documented_fields(async_client):
    created = await create(async_client)

    response = await async_client.get(f"/api/v1/tickets/{created['id']}/trace")

    assert set(response.json()[0]) == TRACE_KEYS


async def test_trace_is_scoped_to_the_requested_ticket(async_client):
    first = await create(async_client, titulo="Primero")
    second = await create(async_client, titulo="Segundo")

    rows = (await async_client.get(f"/api/v1/tickets/{second['id']}/trace")).json()

    assert {row["ticket_id"] for row in rows} == {second["id"]}
    assert second["id"] != first["id"]


async def test_trace_of_an_unknown_ticket_is_a_404(async_client):
    response = await async_client.get("/api/v1/tickets/999999/trace")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket 999999 no encontrado."


async def test_creating_a_ticket_is_unaffected_by_the_trace_endpoint(async_client):
    """Traces are additive: the creation response keeps its own shape."""
    created = await create(async_client)

    assert "traces" not in created
    assert "trace" not in created


# ── Degraded pipeline, through the real adapter ────────────────────────────────

@respx.mock
async def test_a_failing_agent_still_returns_201_and_is_traced_as_failed(async_client, api_app, respx_mock):
    use_real_adapter(api_app)
    # The classifier times out; the other three agents answer normally.
    respx_mock.post(OLLAMA_URL).mock(
        side_effect=[httpx.ReadTimeout("too slow"), agent_reply, agent_reply, agent_reply]
    )

    created = await create(async_client, titulo="Ollama caído", descripcion="Simulación de fallo")

    rows = (await async_client.get(f"/api/v1/tickets/{created['id']}/trace")).json()
    assert len(rows) == 4
    assert [row["success"] for row in rows] == [False, True, True, True]
    assert rows[0]["error_type"] == "ReadTimeout"
    assert rows[0]["raw_output"] is None
    assert all(row["latency_ms"] > 0 for row in rows)


@respx.mock
async def test_traces_from_a_real_run_never_hold_the_full_description(async_client, api_app, respx_mock):
    use_real_adapter(api_app)
    respx_mock.post(OLLAMA_URL).mock(side_effect=agent_reply)
    descripcion = "dato sensible " * 40

    created = await create(async_client, titulo="Fuga", descripcion=descripcion)

    rows = (await async_client.get(f"/api/v1/tickets/{created['id']}/trace")).json()
    assert all(descripcion not in row["input_summary"] for row in rows)
    assert all(len(row["input_summary"]) <= 200 for row in rows)


# ── Trace writing is best-effort ───────────────────────────────────────────────

async def test_a_broken_trace_store_does_not_break_ticket_creation(async_client, api_app):
    class BrokenTraceRepository(InMemoryAgentTraceRepository):
        def add_traces(self, ticket_id, traces):
            raise RuntimeError("trace store unavailable")

    api_app.dependency_overrides[get_agent_trace_repository] = BrokenTraceRepository

    created = await create(async_client)

    assert created["id"] is not None
    assert created["tipo"] == "incidente"
