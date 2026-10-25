"""FastAPI Application for Groww HDFC Mutual Fund Facts Assistant.

Exposes RESTful endpoints for user chat inquiries, scheme factsheet snapshots,
session/thread persistence, and service health monitoring. Designed for
production deployment on Railway.app.
"""

from contextlib import asynccontextmanager
import os
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    MessageSchema,
    SchemeOverview,
    ThreadDetailSchema,
    ThreadSummarySchema,
)
from src.config import config
from src.generation import answer_query
from src.ingestion.crawler import read_manifest
from src.ingestion.indexer import get_chroma_client, get_or_create_collection
from src.state.session_manager import SessionManager
from src.utils.logger import get_logger

logger = get_logger("src.api.main")

# Fixed factual metadata for the 5 canonical Groww HDFC mutual fund schemes
CANONICAL_SCHEMES_METADATA = {
    "hdfc_mid_cap": {
        "risk_level": "High Risk",
        "nav": "₹198.42",
        "change_pct": "+0.84%",
        "expense_ratio": "0.74%",
        "exit_load": "1.0% (<1Y)",
        "fund_size": "₹68,420 Cr",
    },
    "hdfc_small_cap": {
        "risk_level": "Very High Risk",
        "nav": "₹142.15",
        "change_pct": "+1.12%",
        "expense_ratio": "0.68%",
        "exit_load": "1.0% (<1Y)",
        "fund_size": "₹32,150 Cr",
    },
    "hdfc_large_mid_cap": {
        "risk_level": "Very High Risk",
        "nav": "₹284.60",
        "change_pct": "+0.65%",
        "expense_ratio": "0.82%",
        "exit_load": "1.0% (<1Y)",
        "fund_size": "₹19,840 Cr",
    },
    "hdfc_silver_etf_fof": {
        "risk_level": "High Risk",
        "nav": "₹14.85",
        "change_pct": "+2.40%",
        "expense_ratio": "0.35%",
        "exit_load": "0.5% (<15D)",
        "fund_size": "₹1,450 Cr",
    },
    "hdfc_multi_cap": {
        "risk_level": "Very High Risk",
        "nav": "₹21.40",
        "change_pct": "+0.95%",
        "expense_ratio": "0.78%",
        "exit_load": "1.0% (<1Y)",
        "fund_size": "₹14,210 Cr",
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup diagnostics, cache warming, and readiness."""
    logger.info("Initializing Mutual Fund FAQ API server...")
    try:
        from src.ingestion.indexer import get_embedding_function
        # Pre-warm SentenceTransformer singleton into RAM to ensure sub-second response times
        get_embedding_function()

        client = get_chroma_client()
        col = get_or_create_collection(client)
        chunk_count = col.count()
        if chunk_count == 0:
            logger.info("ChromaDB is empty on startup. Auto-indexing canonical corpus...")
            try:
                from src.ingestion.indexer import index_all
                index_all(force_crawl=False)
                chunk_count = col.count()
                logger.info(f"Auto-indexed ChromaDB: {chunk_count} chunks ready.")
            except Exception as ie:
                logger.warning(f"Auto-indexing on startup failed: {ie}")
        logger.info(f"Connected to ChromaDB: collection '{col.name}' has {chunk_count} chunks.")
    except Exception as e:
        logger.warning(f"ChromaDB connection check encountered an issue during startup: {e}")
    yield
    logger.info("Shutting down Mutual Fund FAQ API server.")


app = FastAPI(
    title="Groww | HDFC Mutual Fund Facts Assistant API",
    description="Deterministic, facts-only RAG backend for HDFC Mutual Fund schemes with strict SEBI guardrails.",
    version="1.0.0",
    lifespan=lifespan,
)

# ------------------------------------------------------------------------------
# CORS Middleware
# ------------------------------------------------------------------------------
# Allows requests from Vercel frontend deployments and local dev servers
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins_env == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_session_manager() -> SessionManager:
    """Retrieve SessionManager instance configured with persistent storage."""
    return SessionManager(persist_dir=config.session_persist_path)


# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------

@app.get("/", tags=["Root"])
def root_service_info():
    """Root entrypoint providing service status, API navigation links, and documentation."""
    return {
        "service": "Groww | HDFC Mutual Fund Facts Assistant API",
        "status": "online",
        "documentation": "/docs",
        "health_check": "/health",
        "covered_schemes": "/api/schemes",
        "chat_inquiry": "POST /api/chat",
        "sessions": "/api/sessions",
    }


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check():
    """Health check endpoint for Railway load balancers and container monitoring."""
    try:
        client = get_chroma_client()
        col = get_or_create_collection(client)
        chunk_count = col.count()
    except Exception:
        chunk_count = 0

    return HealthResponse(
        status="healthy",
        service="mutualfund-rag-backend",
        version="1.0.0",
        chromadb_collection=config.chroma_collection_name,
        chunks_indexed=chunk_count,
        embedding_model=config.embedding_model_name,
        llm_model=config.groq_model,
        timestamp=time.time(),
    )


@app.post("/api/admin/reindex", tags=["Admin"])
def trigger_reindex():
    """Trigger on-demand indexing of the 5 canonical Groww scheme pages."""
    try:
        from src.ingestion.indexer import index_all
        summary = index_all(force_crawl=False)
        return {"status": "success", "summary": summary}
    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schemes", response_model=List[SchemeOverview], tags=["Schemes"])
def list_covered_schemes():
    """Fetch factual snapshots for the 5 covered canonical Groww HDFC schemes."""
    try:
        manifest = read_manifest()
        sources = manifest.get("sources", [])
    except Exception:
        sources = []

    schemes: List[SchemeOverview] = []
    for s in sources:
        sid = s["scheme_id"]
        meta = CANONICAL_SCHEMES_METADATA.get(sid, {
            "risk_level": "High Risk",
            "nav": "N/A",
            "change_pct": "0.0%",
            "expense_ratio": "N/A",
            "exit_load": "N/A",
            "fund_size": "N/A",
        })
        schemes.append(
            SchemeOverview(
                scheme_id=sid,
                scheme_name=s["scheme_name"],
                category=s.get("category", "Mutual Fund"),
                url=s["url"],
                risk_level=meta["risk_level"],
                nav=meta["nav"],
                change_pct=meta["change_pct"],
                expense_ratio=meta["expense_ratio"],
                exit_load=meta["exit_load"],
                fund_size=meta["fund_size"],
            )
        )
    return schemes


@app.post("/api/chat", response_model=ChatResponse, tags=["RAG Inquiry"])
def chat_inquiry(request: ChatRequest):
    """Execute end-to-end RAG inquiry with PII & advisory guardrails."""
    start_time = time.time()
    sm = get_session_manager()

    thread_id = request.thread_id
    if not thread_id:
        created_thread = sm.create_thread(title="New Conversation")
        thread_id = created_thread.thread_id

    # Execute full RAG pipeline
    response = answer_query(request.query, thread_id=thread_id)

    # Persist message history in thread
    try:
        sm.add_message(
            role="user",
            content=request.query,
            thread_id=thread_id,
        )
        sm.add_message(
            role="assistant",
            content=response.answer_text,
            citation_url=str(response.citation_url) if response.citation_url else None,
            last_updated=response.last_updated_date.strftime("%Y-%m-%d"),
            is_refusal=response.is_refusal,
            thread_id=thread_id,
        )
    except Exception as e:
        logger.warning(f"Failed to record message history in session {thread_id}: {e}")

    elapsed_ms = (time.time() - start_time) * 1000

    return ChatResponse(
        thread_id=thread_id,
        query=request.query,
        content=response.answer_text,
        citation_url=str(response.citation_url) if response.citation_url else None,
        is_refusal=response.is_refusal,
        refusal_type=response.refusal_type,
        last_updated=response.last_updated_date.strftime("%Y-%m-%d"),
        execution_time_ms=round(elapsed_ms, 2),
    )


@app.get("/api/sessions", response_model=List[ThreadSummarySchema], tags=["Sessions"])
def list_sessions():
    """List all saved conversation sessions ordered by recency."""
    sm = get_session_manager()
    threads = sm.list_threads()
    summaries: List[ThreadSummarySchema] = []
    for t in threads:
        summaries.append(
            ThreadSummarySchema(
                thread_id=t.thread_id,
                title=t.title,
                message_count=t.message_count,
                last_active=t.last_active.isoformat() if hasattr(t.last_active, "isoformat") else str(t.last_active),
            )
        )
    return summaries


@app.post("/api/sessions", response_model=ThreadSummarySchema, status_code=status.HTTP_201_CREATED, tags=["Sessions"])
def create_session(title: Optional[str] = "New Conversation"):
    """Create a new isolated conversation thread."""
    sm = get_session_manager()
    thread = sm.create_thread(title=title or "New Conversation")
    return ThreadSummarySchema(
        thread_id=thread.thread_id,
        title=thread.title,
        message_count=len(thread.messages),
        last_active=thread.updated_at.isoformat(),
    )


@app.get("/api/sessions/{session_id}", response_model=ThreadDetailSchema, tags=["Sessions"])
def get_session_history(session_id: str):
    """Fetch complete message history for a specific conversation thread."""
    sm = get_session_manager()
    if session_id not in sm.threads:
        loaded = sm.load_from_disk(session_id)
        if not loaded:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation thread '{session_id}' not found",
            )

    thread = sm.threads[session_id]
    messages = [
        MessageSchema(
            message_id=m.message_id,
            role=m.role,
            content=m.content,
            citation_url=m.citation_url,
            last_updated=m.last_updated,
            is_refusal=m.is_refusal,
            timestamp=m.timestamp.isoformat() if hasattr(m.timestamp, "isoformat") else str(m.timestamp),
        )
        for m in thread.messages
    ]

    return ThreadDetailSchema(
        thread_id=thread.thread_id,
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
        messages=messages,
    )


@app.delete("/api/sessions/{session_id}", tags=["Sessions"])
def delete_session(session_id: str):
    """Delete a conversation thread and remove its persistent disk file."""
    sm = get_session_manager()
    deleted = sm.delete_thread(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation thread '{session_id}' not found",
        )
    return {"status": "deleted", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    raw_port = os.getenv("PORT", "8000")
    try:
        port = int(raw_port)
    except (ValueError, TypeError):
        logger.warning(f"Invalid or non-integer PORT '{raw_port}', falling back to 8000")
        port = 8000
    reload_flag = os.getenv("API_RELOAD", "false").lower() in ("true", "1", "yes")
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=reload_flag)
