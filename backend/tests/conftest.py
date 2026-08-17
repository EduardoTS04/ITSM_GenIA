"""Shared test fixtures.

app.main creates its engine and runs create_all at import time, so DATABASE_URL
is pointed at a throwaway file *before* app.main is imported. That keeps the real
data/itsm.db untouched by the suite.
"""

import os
import socket
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

_IMPORT_TIME_DB = Path(tempfile.mkdtemp(prefix="itsm_import_")) / "itsm.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _IMPORT_TIME_DB.as_posix()
# Guarantees no test can reach a developer's real Ollama instance by accident.
os.environ["OLLAMA_BASE_URL"] = "http://ollama.invalid:11434"

import httpx  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.domain.entities.agent_trace import AgentTrace  # noqa: E402,F401  (registers the table)
from app.domain.entities.comment import Comment  # noqa: E402,F401  (registers the table)
from app.domain.entities.ticket import Ticket  # noqa: E402,F401  (registers the table)
from app.infrastructure.database.connection import Base, get_db  # noqa: E402
from app.infrastructure.db.agent_trace_repository import SqlAlchemyAgentTraceRepository  # noqa: E402
from app.infrastructure.db.ticket_repository import SqlAlchemyTicketRepository  # noqa: E402
from app.main import app  # noqa: E402
from app.presentation.api.deps import get_llm_agent  # noqa: E402

from tests.fakes import FakeLLMAgent  # noqa: E402


# ── Network guard ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly if a test tries to reach a real host (e.g. a live Ollama).

    Only name resolution and the outbound-connection helpers are blocked.
    `socket.socket.connect` itself must keep working: asyncio's Windows event
    loop builds its self-pipe from a loopback socketpair.
    """

    def deny(*args, **kwargs):
        raise RuntimeError("Network access is not allowed in tests; mock it instead.")

    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket, "gethostbyname", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


# ── Database ───────────────────────────────────────────────────────────────────

@pytest.fixture
def db_engine(tmp_path: Path):
    """A real SQLite database on a per-test temp file, with the full schema."""
    engine = create_engine(
        "sqlite:///" + (tmp_path / "test.db").as_posix(),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Iterator[Session]:
    session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def ticket_repository(db_session: Session) -> SqlAlchemyTicketRepository:
    return SqlAlchemyTicketRepository(db_session)


@pytest.fixture
def trace_repository(db_session: Session) -> SqlAlchemyAgentTraceRepository:
    return SqlAlchemyAgentTraceRepository(db_session)


# ── LLM port ───────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_agent() -> FakeLLMAgent:
    return FakeLLMAgent()


# ── API clients ────────────────────────────────────────────────────────────────

@pytest.fixture
def api_app(db_session: Session, fake_agent: FakeLLMAgent):
    """The FastAPI app with the DB session and the LLM port overridden."""

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm_agent] = lambda: fake_agent
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def async_client(api_app) -> Iterator[httpx.AsyncClient]:
    """httpx.AsyncClient talking to the app in-process; no sockets involved."""
    transport = httpx.ASGITransport(app=api_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
