"""Unit tests for the agent pipeline and its LLMAgentPort adapter.

Every Ollama call is intercepted by `respx`, so no network is touched.
"""

import asyncio
import json

import httpx
import respx

from app.agents import orchestrator
from app.agents.orchestrator import OllamaConfig
from app.infrastructure.llm.ollama_orchestrator_adapter import OllamaOrchestratorAdapter

# The pipeline takes its target from the caller, so tests state it explicitly
# instead of relying on environment variables.
BASE_URL = "http://ollama.invalid:11434"
MODEL = "llama3.2"
OLLAMA_URL = f"{BASE_URL}/api/chat"


def build_config(model: str = MODEL, max_retries: int = 2) -> OllamaConfig:
    # Zero backoff keeps the retry tests instant.
    return OllamaConfig(
        base_url=BASE_URL,
        model=model,
        timeout_seconds=5.0,
        max_retries=max_retries,
        backoff_seconds=0.0,
    )


async def run_pipeline(titulo: str = "t", descripcion: str = "d", model: str = MODEL,
                       max_retries: int = 2) -> orchestrator.PipelineRun:
    return await orchestrator.orchestrate(
        titulo=titulo,
        descripcion=descripcion,
        config=build_config(model=model, max_retries=max_retries),
    )


async def orchestrate(titulo: str = "t", descripcion: str = "d", model: str = MODEL,
                      max_retries: int = 2) -> dict:
    run = await run_pipeline(titulo=titulo, descripcion=descripcion, model=model,
                             max_retries=max_retries)
    return run.analysis


def build_adapter(model: str = MODEL) -> OllamaOrchestratorAdapter:
    return OllamaOrchestratorAdapter(build_config(model=model))


CLASIFICADOR = {
    "tipo": "problema", "categoria": "Red", "subcategoria": "VPN",
    "confianza": 0.87, "razon": "Patrón de fallo de red.",
}
PRIORIZADOR = {
    "prioridad": "P1", "impacto": "alto", "urgencia": "alta",
    "area_responsable": "Infraestructura", "razon": "Producción detenida.",
}
SOPORTE = {
    "saludo": "Hola, entendemos tu problema.",
    "pasos_solucion": [{"numero": 1, "titulo": "Reiniciar VPN", "descripcion": "Cierra y abre el cliente."}],
    "tiempo_estimado": "20 minutos",
    "cierre": "Escríbenos si continúa.",
}
ANALITICO = {"es_recurrente": True, "causa_raiz": "Certificado vencido", "accion_preventiva": "Renovar antes del vencimiento"}


def _agent_reply(request: httpx.Request) -> httpx.Response:
    """Answer each agent according to the system prompt it sent."""
    system = json.loads(request.content)["messages"][0]["content"]
    if "clasificador" in system:
        payload = CLASIFICADOR
    elif "priorización" in system:
        payload = PRIORIZADOR
    elif "soporte TI" in system:
        payload = SOPORTE
    else:
        payload = ANALITICO
    return httpx.Response(200, json={"message": {"content": json.dumps(payload)}})


def _stub_all_agents(mock: respx.MockRouter) -> None:
    mock.post(OLLAMA_URL).mock(side_effect=_agent_reply)


def _stub_constant(mock: respx.MockRouter, content: str) -> None:
    mock.post(OLLAMA_URL).mock(
        return_value=httpx.Response(200, json={"message": {"content": content}})
    )


def _sent_payloads(mock: respx.MockRouter) -> list[dict]:
    return [json.loads(call.request.content) for call in mock.calls]


# ── Happy path: all four agents answer ─────────────────────────────────────────

@respx.mock
async def test_orchestrate_combines_all_four_agents(respx_mock):
    _stub_all_agents(respx_mock)

    result = await orchestrate(titulo="VPN caída", descripcion="No conecta al ERP")

    assert len(respx_mock.calls) == 4
    assert result["tipo"] == "problema"
    assert result["categoria"] == "Red"
    assert result["subcategoria"] == "VPN"
    assert result["confianza_clasificacion"] == 0.87
    assert result["razon_clasificacion"] == "Patrón de fallo de red."
    assert result["prioridad"] == "P1"
    assert result["impacto"] == "alto"
    assert result["urgencia"] == "alta"
    assert result["area_responsable"] == "Infraestructura"
    assert result["razon_prioridad"] == "Producción detenida."
    assert result["respuesta_estructurada"]["tiempo_estimado"] == "20 minutos"
    assert result["es_recurrente"] is True
    assert result["causa_raiz"] == "Certificado vencido"
    assert result["accion_preventiva"] == "Renovar antes del vencimiento"


@respx.mock
async def test_orchestrate_renders_plaintext_answer_from_the_steps(respx_mock):
    _stub_all_agents(respx_mock)

    result = await orchestrate()

    assert result["respuesta_usuario"] == (
        "Hola, entendemos tu problema.\n\n"
        "1. Reiniciar VPN: Cierra y abre el cliente.\n\n"
        "Escríbenos si continúa."
    )


@respx.mock
async def test_requests_ask_for_non_streaming_json_from_the_configured_model(respx_mock):
    _stub_all_agents(respx_mock)

    await orchestrate()

    sent = _sent_payloads(respx_mock)[0]
    assert sent["model"] == MODEL
    assert sent["stream"] is False
    assert sent["format"] == "json"
    assert [m["role"] for m in sent["messages"]] == ["system", "user"]


@respx.mock
async def test_the_injected_model_is_the_one_requested(respx_mock):
    """The model comes from settings via the caller, not from a hardcoded value."""
    _stub_all_agents(respx_mock)

    await orchestrate(model="mistral-small")

    assert all(sent["model"] == "mistral-small" for sent in _sent_payloads(respx_mock))


@respx.mock
async def test_the_injected_base_url_is_the_one_called(respx_mock):
    _stub_all_agents(respx_mock)

    await orchestrate()

    assert all(str(call.request.url) == OLLAMA_URL for call in respx_mock.calls)


@respx.mock
async def test_later_agents_receive_earlier_results_as_context(respx_mock):
    _stub_all_agents(respx_mock)

    await orchestrate()

    priorizador_user_msg = _sent_payloads(respx_mock)[1]["messages"][1]["content"]
    assert "Clasificación previa" in priorizador_user_msg
    assert "problema" in priorizador_user_msg


@respx.mock
async def test_adapter_maps_the_pipeline_onto_the_typed_port(respx_mock):
    _stub_all_agents(respx_mock)

    analysis = await build_adapter().analyze(titulo="t", descripcion="d")

    assert analysis.tipo == "problema"
    assert analysis.prioridad == "P1"
    assert analysis.confianza_clasificacion == 0.87
    assert analysis.area_responsable == "Infraestructura"
    assert analysis.es_recurrente is True
    assert analysis.respuesta_estructurada["saludo"] == "Hola, entendemos tu problema."


# ── Degraded paths: Ollama unreachable or answering badly ──────────────────────

def _assert_all_fallbacks(result):
    assert result["tipo"] == "incidente"
    assert result["categoria"] == "General"
    assert result["subcategoria"] is None
    assert result["confianza_clasificacion"] == 0.5
    assert result["prioridad"] == "P3"
    assert result["impacto"] == "medio"
    assert result["urgencia"] == "media"
    assert result["area_responsable"] == "Helpdesk"
    assert result["es_recurrente"] is False
    assert result["causa_raiz"] is None
    assert result["accion_preventiva"] is None
    # The support agent falls back to a canned two-step answer, never an empty one.
    assert result["respuesta_estructurada"]["tiempo_estimado"] == "15-30 minutos"
    assert len(result["respuesta_estructurada"]["pasos_solucion"]) == 2


@respx.mock
async def test_connection_error_falls_back_without_raising(respx_mock):
    respx_mock.post(OLLAMA_URL).mock(side_effect=httpx.ConnectError("refused"))

    _assert_all_fallbacks(await orchestrate())


@respx.mock
async def test_timeout_falls_back_without_raising(respx_mock):
    respx_mock.post(OLLAMA_URL).mock(side_effect=httpx.ReadTimeout("too slow"))

    _assert_all_fallbacks(await orchestrate())


@respx.mock
async def test_http_error_falls_back_without_raising(respx_mock):
    respx_mock.post(OLLAMA_URL).mock(return_value=httpx.Response(500, json={"error": "boom"}))

    _assert_all_fallbacks(await orchestrate())


@respx.mock
async def test_non_json_model_output_falls_back(respx_mock):
    _stub_constant(respx_mock, "esto no es JSON")

    _assert_all_fallbacks(await orchestrate())


@respx.mock
async def test_unexpected_error_falls_back(respx_mock):
    """A non-string content makes json.loads raise something we do not enumerate."""
    respx_mock.post(OLLAMA_URL).mock(return_value=httpx.Response(200, json={"message": {"content": 12345}}))

    _assert_all_fallbacks(await orchestrate())


@respx.mock
async def test_unexpected_response_envelope_falls_back(respx_mock):
    respx_mock.post(OLLAMA_URL).mock(return_value=httpx.Response(200, json={"unexpected": "shape"}))

    _assert_all_fallbacks(await orchestrate())


@respx.mock
async def test_adapter_degrades_with_the_pipeline(respx_mock):
    respx_mock.post(OLLAMA_URL).mock(side_effect=httpx.ConnectError("refused"))

    analysis = await build_adapter().analyze(titulo="t", descripcion="d")

    assert analysis.tipo == "incidente"
    assert analysis.categoria == "General"
    assert analysis.prioridad == "P3"
    assert analysis.es_recurrente is False
    # NOTE: once G11 lands, assert the degraded flag is propagated here too.


@respx.mock
async def test_legacy_support_schema_is_converted_into_steps(respx_mock):
    """An older model answer that only has `respuesta_usuario` is still usable."""
    _stub_constant(respx_mock, json.dumps({"respuesta_usuario": "Reinicia el equipo."}))

    result = await orchestrate()

    structured = result["respuesta_estructurada"]
    assert structured["saludo"] == "Hemos recibido tu reporte."
    assert structured["pasos_solucion"][0]["descripcion"] == "Reinicia el equipo."
    assert structured["tiempo_estimado"] == "Variable"


# ── Retry policy ───────────────────────────────────────────────────────────────

@respx.mock
async def test_timeout_is_retried_and_a_later_attempt_still_succeeds(respx_mock):
    route = respx_mock.post(OLLAMA_URL).mock(
        side_effect=[httpx.ReadTimeout("slow"), _agent_reply, _agent_reply, _agent_reply, _agent_reply]
    )

    result = await orchestrate()

    # 4 agents + 1 retry of the first, and the pipeline still gets real values.
    assert route.call_count == 5
    assert result["tipo"] == "problema"
    assert result["prioridad"] == "P1"


@respx.mock
async def test_connection_errors_are_retried_up_to_max_retries(respx_mock):
    route = respx_mock.post(OLLAMA_URL).mock(side_effect=httpx.ConnectError("refused"))

    await orchestrate(max_retries=2)

    # 3 attempts (1 + 2 retries) for each of the 4 agents.
    assert route.call_count == 12


@respx.mock
async def test_http_errors_are_not_retried(respx_mock):
    route = respx_mock.post(OLLAMA_URL).mock(return_value=httpx.Response(400, json={"error": "bad model"}))

    await orchestrate(max_retries=2)

    assert route.call_count == 4


@respx.mock
async def test_backoff_grows_exponentially_between_retries(respx_mock, monkeypatch):
    respx_mock.post(OLLAMA_URL).mock(side_effect=httpx.ConnectError("refused"))
    delays: list[float] = []

    async def record(delay):
        delays.append(delay)

    monkeypatch.setattr(orchestrator.asyncio, "sleep", record)
    config = OllamaConfig(
        base_url=BASE_URL, model=MODEL, timeout_seconds=5.0, max_retries=2, backoff_seconds=0.5
    )

    await orchestrator.call_ollama(
        httpx.AsyncClient(), orchestrator.CLASIFICADOR_SYSTEM, "u", config,
        "clasificador", "resumen",
    )

    assert delays == [0.5, 1.0]


@respx.mock
async def test_a_hanging_call_leaves_the_event_loop_free(respx_mock):
    """A slow Ollama call must not block other coroutines, then still fall back."""
    sibling_done = asyncio.Event()

    async def hang(request: httpx.Request) -> httpx.Response:
        await asyncio.wait_for(sibling_done.wait(), timeout=5)
        raise httpx.ReadTimeout("too slow")

    async def sibling():
        sibling_done.set()
        return "done"

    respx_mock.post(OLLAMA_URL).mock(side_effect=hang)

    result, sibling_result = await asyncio.gather(orchestrate(max_retries=0), sibling())

    assert sibling_result == "done"
    _assert_all_fallbacks(result)


# ── Execution trace (G15) ──────────────────────────────────────────────────────

@respx.mock
async def test_every_agent_call_produces_one_trace(respx_mock):
    _stub_all_agents(respx_mock)

    run = await run_pipeline(titulo="VPN caída", descripcion="No conecta al ERP")

    assert [t.agent_name for t in run.traces] == ["clasificador", "priorizador", "soporte", "analitico"]
    assert all(t.success for t in run.traces)
    assert all(t.latency_ms > 0 for t in run.traces)
    assert all(t.error_type is None for t in run.traces)
    assert all(t.prompt_version == orchestrator.PROMPT_VERSION for t in run.traces)


@respx.mock
async def test_trace_keeps_the_raw_model_answer(respx_mock):
    _stub_all_agents(respx_mock)

    run = await run_pipeline()

    assert json.loads(run.traces[0].raw_output) == CLASIFICADOR


@respx.mock
async def test_trace_of_a_failed_call_names_the_error_and_has_no_output(respx_mock):
    respx_mock.post(OLLAMA_URL).mock(side_effect=httpx.ReadTimeout("too slow"))

    run = await run_pipeline(max_retries=0)

    assert len(run.traces) == 4
    assert all(t.success is False for t in run.traces)
    assert all(t.error_type == "ReadTimeout" for t in run.traces)
    assert all(t.raw_output is None for t in run.traces)


@respx.mock
async def test_only_the_failing_agent_is_traced_as_failed(respx_mock):
    """The first agent times out; the remaining three answer normally."""
    respx_mock.post(OLLAMA_URL).mock(
        side_effect=[httpx.ReadTimeout("slow"), _agent_reply, _agent_reply, _agent_reply]
    )

    run = await run_pipeline(max_retries=0)

    assert [t.success for t in run.traces] == [False, True, True, True]
    assert run.traces[0].error_type == "ReadTimeout"
    assert [t.error_type for t in run.traces[1:]] == [None, None, None]


@respx.mock
async def test_a_retried_call_that_succeeds_is_traced_as_successful(respx_mock):
    respx_mock.post(OLLAMA_URL).mock(
        side_effect=[httpx.ConnectError("refused"), _agent_reply, _agent_reply, _agent_reply, _agent_reply]
    )

    run = await run_pipeline()

    assert run.traces[0].success is True
    assert run.traces[0].error_type is None


@respx.mock
async def test_trace_of_a_bad_status_names_the_http_error(respx_mock):
    respx_mock.post(OLLAMA_URL).mock(return_value=httpx.Response(500, json={"error": "boom"}))

    run = await run_pipeline()

    assert all(t.error_type == "HTTPStatusError" for t in run.traces)


@respx.mock
async def test_trace_keeps_unparseable_output_for_debugging(respx_mock):
    _stub_constant(respx_mock, "esto no es JSON")

    run = await run_pipeline()

    assert run.traces[0].success is False
    assert run.traces[0].error_type == "JSONDecodeError"
    assert run.traces[0].raw_output == "esto no es JSON"


@respx.mock
async def test_trace_input_summary_is_truncated(respx_mock):
    _stub_all_agents(respx_mock)

    run = await run_pipeline(titulo="Título largo", descripcion="x" * 500)

    summary = run.traces[0].input_summary
    assert len(summary) == orchestrator.INPUT_SUMMARY_MAX_LEN
    assert summary.startswith("Título largo — xxx")
    assert summary.endswith("…")
    # The full description must not be recoverable from the trace.
    assert "x" * 500 not in summary


@respx.mock
async def test_trace_input_summary_keeps_short_inputs_whole(respx_mock):
    _stub_all_agents(respx_mock)

    run = await run_pipeline(titulo="VPN caída", descripcion="No conecta")

    assert run.traces[0].input_summary == "VPN caída — No conecta"


@respx.mock
async def test_adapter_passes_the_traces_through_the_port(respx_mock):
    _stub_all_agents(respx_mock)

    analysis = await build_adapter().analyze(titulo="t", descripcion="d")

    assert [t.agent_name for t in analysis.traces] == ["clasificador", "priorizador", "soporte", "analitico"]
