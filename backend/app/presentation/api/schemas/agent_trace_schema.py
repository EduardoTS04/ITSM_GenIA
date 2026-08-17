"""Pydantic schemas for the agent execution trace API"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AgentTraceOut(BaseModel):
    """One agent call recorded during ticket creation."""

    id: int
    ticket_id: int
    agent_name: str = Field(..., example="clasificador")
    prompt_version: str = Field(..., example="v1")
    input_summary: Optional[str] = None
    raw_output: Optional[str] = None
    latency_ms: int = Field(..., example=842)
    success: bool
    error_type: Optional[str] = Field(None, example="ReadTimeout")
    created_at: datetime

    class Config:
        from_attributes = True
