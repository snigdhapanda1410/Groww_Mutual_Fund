"""Pydantic schemas for the Mutual Fund FAQ Assistant REST API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming user chat query."""
    query: str = Field(..., min_length=1, max_length=2000, description="User's query string")
    thread_id: Optional[str] = Field(None, description="Optional conversation thread/session ID")


class ChatResponse(BaseModel):
    """Outgoing RAG response payload adhering to facts-only output contract."""
    thread_id: str = Field(..., description="Active thread/session ID")
    query: str = Field(..., description="Original user query")
    content: str = Field(..., description="Compliant assistant response or refusal message")
    citation_url: Optional[str] = Field(None, description="Authoritative Groww scheme URL")
    is_refusal: bool = Field(False, description="Whether guardrails blocked or refused the query")
    refusal_type: Optional[str] = Field(None, description="'advisory', 'pii', or 'out_of_scope'")
    last_updated: str = Field(..., description="Date stamp of source factsheet")
    execution_time_ms: float = Field(..., description="End-to-end latency in milliseconds")


class SchemeOverview(BaseModel):
    """Summary of a covered HDFC mutual fund scheme."""
    scheme_id: str
    scheme_name: str
    category: str
    url: str
    risk_level: str
    nav: str
    change_pct: str
    expense_ratio: str
    exit_load: str
    fund_size: str


class ThreadSummarySchema(BaseModel):
    """High-level metadata for conversation threads."""
    thread_id: str
    title: str
    message_count: int
    last_active: str


class MessageSchema(BaseModel):
    """Individual chat message."""
    message_id: str
    role: str
    content: str
    citation_url: Optional[str] = None
    last_updated: Optional[str] = None
    is_refusal: bool = False
    timestamp: str


class ThreadDetailSchema(BaseModel):
    """Complete conversation thread history."""
    thread_id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[MessageSchema]


class HealthResponse(BaseModel):
    """Service health and vector collection status."""
    status: str
    service: str
    version: str
    chromadb_collection: str
    chunks_indexed: int
    embedding_model: str
    llm_model: str
    timestamp: float
