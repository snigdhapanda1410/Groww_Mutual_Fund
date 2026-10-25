"""Data models and Pydantic schemas for the Mutual Fund FAQ Assistant."""

from datetime import date, datetime
from typing import List, Literal, Optional
import uuid
from pydantic import BaseModel, Field, HttpUrl, field_validator


class DocumentChunk(BaseModel):
    """A single indexed chunk from an official mutual fund document or scheme page."""

    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    scheme_id: str  # e.g., "hdfc_mid_cap"
    scheme_name: str  # e.g., "HDFC Mid-Cap Opportunities Fund (Direct - Growth)"
    category: str  # e.g., "Equity: Mid Cap"
    doc_type: str = "GrowwPage"  # e.g., "GrowwPage", "KIM", "SID", "Factsheet"
    source_url: HttpUrl  # Canonical source URL (Groww scheme page)
    groww_url: Optional[HttpUrl] = None
    publish_date: date
    section: str  # e.g., "Expense Ratio & Exit Load"
    content: str  # Markdown table or prose content
    content_type: Literal["text", "table", "list"] = "text"
    page_number: Optional[int] = None
    token_count: Optional[int] = None


class QueryIntentResult(BaseModel):
    """Result of the pre-retrieval intent classification & safety pipeline."""

    original_query: str
    is_factual: bool
    is_advisory: bool
    has_pii: bool
    pii_type: Optional[str] = None  # e.g., "PAN", "Aadhaar", "Mobile", "Folio"
    detected_scheme_id: Optional[str] = None
    detected_topic: Optional[str] = None
    refusal_reason: Optional[str] = None
    classification_method: Literal["regex", "llm", "hybrid"] = "hybrid"


class RetrievedContext(BaseModel):
    """A retrieved context chunk along with its ranking and similarity score."""

    chunk: DocumentChunk
    similarity_score: float
    rank: int


class AssistantResponse(BaseModel):
    """The final validated response delivered to the user adhering to Output Contract."""

    answer_text: str
    sentence_count: int
    citation_url: HttpUrl
    last_updated_date: date
    is_refusal: bool = False
    thread_id: str = ""
    refusal_type: Optional[str] = None

    @field_validator("sentence_count")
    @classmethod
    def validate_sentence_count(cls, v: int) -> int:
        if v > 3:
            raise ValueError(f"Response has {v} sentences; max allowed is 3")
        return v

    def formatted_output(self) -> str:
        """Render display-ready response string with citation badge and date footer."""
        if self.is_refusal:
            return self.answer_text
        return (
            f"{self.answer_text}\n\n"
            f"**Source**: [{self.citation_url}]({self.citation_url})\n\n"
            f"*Last updated from sources: {self.last_updated_date.strftime('%Y-%m-%d')}*"
        )


class Message(BaseModel):
    """A single turn in a conversation thread."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: Literal["user", "assistant", "system"]
    content: str
    citation_url: Optional[str] = None
    last_updated: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_refusal: bool = False


class Thread(BaseModel):
    """An independent conversation thread containing a series of messages."""

    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = "New Conversation"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: List[Message] = Field(default_factory=list)


class ThreadSummary(BaseModel):
    """Lightweight summary metadata for the sidebar thread list."""

    thread_id: str
    title: str
    message_count: int
    last_active: datetime
