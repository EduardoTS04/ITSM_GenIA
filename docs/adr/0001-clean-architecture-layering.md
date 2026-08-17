# ADR 0001 — Clean architecture layering

**Status:** Accepted  
**Date:** 2026-08-17

## Context

Ticket HTTP handlers originally built SQLAlchemy `Ticket` objects, ran `db.query(...)`, and called `orchestrate()` inline. That mixed transport, persistence, and the LLM pipeline in one module, so the create path could not be unit-tested without FastAPI, a real database, and a live Ollama.

Comments still look like that original style (`comments.py` uses `get_db` and `db.query`). The create-ticket path was the first to change because it is the longest and the one that talks to the model.

## Decision

Split the backend along ports-and-adapters lines, using the packages that exist today:

- `app/domain/ports.py` defines `TicketRepository`, `AgentTraceRepository`, and `LLMAgentPort`. Domain entities remain SQLAlchemy models under `app/domain/entities/` (a pragmatic compromise, not a pure domain model).
- `app/application/use_cases/create_ticket.py` owns “analyze, then persist ticket, then persist traces”.
- `app/infrastructure/db/` and `app/infrastructure/llm/` implement the ports.
- `app/presentation/api/deps.py` wires implementations with FastAPI `Depends`.

List/get/escalate tickets depend on `TicketRepository` from the router but do not have their own use-case classes. That is intentional scope, not an unfinished diagram in the README.

## Consequences

**Positive**

- `CreateTicketUseCase` is tested with `FakeLLMAgent` and `InMemoryTicketRepository` (`backend/tests/fakes.py`) with no HTTP or SQLite.
- The Ollama adapter can change (sync `requests` → async httpx) without touching the router.
- Trace persistence is a second port, so a broken trace store cannot be confused with a failed ticket insert.

**Negative**

- Two persistence styles coexist: tickets/traces go through ports; comments do not.
- Entities import `Base` from infrastructure, so the domain package is not framework-free.
- Callers must remember that only create-ticket is a use-case; treating every router as a thin shell would be inaccurate.
