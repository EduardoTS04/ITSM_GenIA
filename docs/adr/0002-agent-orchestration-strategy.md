# ADR 0002 — Sequential agents with typed fallbacks

**Status:** Accepted  
**Date:** 2026-08-17

## Context

Creating a ticket needs four distinct LLM jobs: classification, prioritization, a user-facing answer, and a recurrence/root-cause note. They could run in parallel, or the pipeline could abort when Ollama fails. Priorizador prompts include the clasificador JSON; soporte and analítico prompts include both classification and prioritization. A failed or empty model response used to have to become *some* valid `Ticket` row, because the API contract is “always 201 with a ticket”, not “502 when the model is down”.

## Decision

Keep a **strict sequence** in `app/agents/orchestrator.py`:

1. `agente_clasificador`
2. `agente_priorizador` (input includes step 1)
3. `agente_soporte` (steps 1–2)
4. `agente_analitico` (steps 1–2)

Each `call_ollama` is async httpx with a configurable timeout, retries only for connection errors and timeouts, and fail-fast on HTTP error status. On any failure the helper returns `{}`. Each agent then fills a **typed default dict** (for example tipo `incidente`, prioridad `P3`, canned support steps) rather than raising. The merged analysis is always persistable.

Each call also yields an `AgentTraceRecord` (latency, success, exception class name, truncated input summary, raw model text). Traces are stored after the ticket exists and must not fail creation.

Soporte and analítico do **not** run in parallel today, even though they share the same upstream context. Parallelism is a later change; this ADR records the current choice.

## Consequences

**Positive**

- Prioridad and the support answer are conditioned on the same classification the API stores, not on a race of four independent guesses.
- Ticket creation stays available when Ollama is down; traces show `success: false` and `error_type` instead of an empty 500.
- Tests can stub a single `/api/chat` route and assert both fallbacks and the four-row trace.

**Negative**

- Latency is roughly the sum of four model calls (and their retries), not the max.
- A bad classification is fed forward; later agents do not get a second unconditioned look at the raw ticket.
- Defaults can hide a total outage unless the caller reads `/tickets/{id}/trace`.
- Retrying timeouts can make a single create request last many minutes (`OLLAMA_TIMEOUT_SECONDS` × attempts × four agents).
