"""SQLAlchemy ORM model for AgentTrace entity.

One row per agent call made while creating a ticket. This is observability data:
it is written on a best-effort basis and is never required for a ticket to exist.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from datetime import datetime
from app.infrastructure.database.connection import Base

class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String, nullable=False)  # clasificador|priorizador|soporte|analitico
    prompt_version = Column(String, nullable=False, default="v1")
    # Truncated view of the ticket input, never the full raw description.
    input_summary = Column(Text, nullable=True)
    raw_output = Column(Text, nullable=True)  # raw model answer, null when the call never returned one
    latency_ms = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False, default=False)
    error_type = Column(String, nullable=True)  # exception class name when success is false
    created_at = Column(DateTime, default=datetime.utcnow)
