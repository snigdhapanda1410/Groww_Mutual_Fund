# 🚀 Deployment Plan: Mutual Fund FAQ Assistant
## Decoupled Architecture: Backend on Railway · Frontend on Vercel

> **Project**: Groww-Inspired HDFC Mutual Fund Facts-Only RAG Assistant  
> **Backend Host**: [Railway.app](https://railway.app/) (Containerized FastAPI + ChromaDB + Persistent Volume)  
> **Frontend Host**: [Vercel](https://vercel.com/) (Edge-Optimized Web Application / Static SPA)  
> **Architecture Reference**: [`Docs/architecture.md`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md)  
> **Implementation Reference**: [`Docs/implementation-plan.md`](file:///c:/Projects/Mutualfund_RAG/Docs/implementation-plan.md)  

---

## 📑 Table of Contents

1. [Executive Summary & Architectural Rationale](#1-executive-summary--architectural-rationale)
2. [High-Level Deployment Topology](#2-high-level-deployment-topology)
3. [Decoupling Strategy: Streamlit to Client-Server](#3-decoupling-strategy-streamlit-to-client-server)
4. [Backend Deployment on Railway](#4-backend-deployment-on-railway)
   - [4.1 API Architecture & FastAPI Endpoints](#41-api-architecture--fastapi-endpoints)
   - [4.2 Railway Dockerfile & Build Configuration](#42-railway-dockerfile--build-configuration)
   - [4.3 Persistent Storage & Volume Strategy](#43-persistent-storage--volume-strategy)
   - [4.4 Railway Environment Variables](#44-railway-environment-variables)
5. [Frontend Deployment on Vercel](#5-frontend-deployment-on-vercel)
   - [5.1 Frontend Tech Stack Options](#51-frontend-tech-stack-options)
   - [5.2 Vercel Configuration & Reverse Proxy](#52-vercel-configuration--reverse-proxy)
   - [5.3 Groww Obsidian Emerald UI Integration](#53-groww-obsidian-emerald-ui-integration)
   - [5.4 Vercel Environment Variables](#54-vercel-environment-variables)
6. [Daily Ingestion Scheduler CI/CD Integration](#6-daily-ingestion-scheduler-cicd-integration)
7. [Step-by-Step Implementation & Rollout Plan](#7-step-by-step-implementation--rollout-plan)
   - [Phase D1: Backend API Scaffold & FastAPI Layer](#phase-d1-backend-api-scaffold--fastapi-layer)
   - [Phase D2: Containerization & Railway Provisioning](#phase-d2-containerization--railway-provisioning)
   - [Phase D3: Frontend Client Packaging & Vercel Setup](#phase-d3-frontend-client-packaging--vercel-setup)
   - [Phase D4: Networking, CORS & Reverse Proxy Wiring](#phase-d4-networking-cors--reverse-proxy-wiring)
   - [Phase D5: End-to-End Verification & Health Checks](#phase-d5-end-to-end-verification--health-checks)
8. [Acceptance Gate & Smoke Test Matrix](#8-acceptance-gate--smoke-test-matrix)
9. [Cost, Sizing & Resource Allocation](#9-cost-sizing--resource-allocation)
10. [Runbooks, Troubleshooting & Disaster Recovery](#10-runbooks-troubleshooting--disaster-recovery)

---

## 1. Executive Summary & Architectural Rationale

This deployment plan outlines the transformation of the monolithic Streamlit-based **Mutual Fund FAQ Assistant** into a production-grade, decoupled client-server architecture:

1. **Backend on Railway**:
   - Runs as a persistent, high-throughput containerized **FastAPI** service.
   - Hosts the offline-ingested **ChromaDB** vector database backed by a **Railway Persistent Volume** (`/app/data`).
   - Executes local embedding generation using `sentence-transformers/all-MiniLM-L6-v2`.
   - Enforces two-tier safety guardrails (Indian financial PII redaction and advisory refusal classifiers).
   - Interfaces securely with Groq Cloud for `openai/gpt-oss-120b` inference with sliding-window rate limiting.
   - Maintains conversation history via file-backed session management.

2. **Frontend on Vercel**:
   - Deployed on Vercel's global CDN for sub-50ms Time-to-First-Byte (TTFB).
   - Implements the custom **Groww Obsidian Emerald dark mode design system** (`#121212`, `#00D09C`).
   - Interacts with the Railway backend via secure HTTPS REST endpoints with automatic reverse proxy routing (`/api/:path*`), eliminating cross-origin resource sharing (CORS) friction.
   - Guarantees complete compliance visibility: non-dismissible SEBI disclaimer banners, verified Groww scheme citation cards, and distinct amber refusal alerts.

---

## 2. High-Level Deployment Topology

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                 END USER BROWSER                                 │
└────────────────────────┬───────────────────────────────────▲─────────────────────┘
                         │ 1. HTTPS Request                  │ 6. Rendered Response
                         ▼                                   │
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           VERCEL EDGE NETWORK (Frontend)                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │ Groww Obsidian Emerald UI (Next.js / Static SPA)                           │  │
│  │ • Persistent SEBI Disclaimer Banner                                        │  │
│  │ • 5 Scheme Snapshot Cards (NAV, TER, Exit Load, AUM)                       │  │
│  │ • Quick Prompt Chips & Multi-Thread Sidebar                                │  │
│  │ • Reverse Proxy Rewrite: /api/* ──► Railway Backend                        │  │
│  └─────────────────────────────────────┬──────────────────────────────────────┘  │
└────────────────────────────────────────┼─────────────────────────────────────────┘
                                         │ 2. Reverse Proxy Request
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             RAILWAY.APP (Backend Service)                        │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │ FastAPI Application Container (Uvicorn / Python 3.11)                      │  │
│  │                                                                            │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ 1. Guardrails Orchestrator: PII Interception & Advisory Classifier   │  │  │
│  │  └──────────────────────────────────┬───────────────────────────────────┘  │  │
│  │                                     ▼                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ 2. Retrieval Engine: Entity Extractor + Cosine Vector Search         │  │  │
│  │  └──────────────────────────────────┬───────────────────────────────────┘  │  │
│  │                                     ▼                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ 3. Generation Engine: Groq LLM Client (openai/gpt-oss-120b)          │  │  │
│  │  │    + Output Contract Validator (≤ 3 sentences, 1 Groww citation)     │  │  │
│  │  └──────────────────────────────────┬───────────────────────────────────┘  │  │
│  │                                     ▼                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ 4. Session Manager: Disk-Backed Thread History                       │  │  │
│  │  └──────────────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────┬──────────────────────────────────────┘  │
│                                        │                                         │
│       ┌────────────────────────────────┴────────────────────────────────┐        │
│       ▼                                                                 ▼        │
│  ┌──────────────────────────────────────────┐  ┌──────────────────────────────┐  │
│  │ Railway Persistent Volume (/app/data)    │  │ Groq Cloud LLM API           │  │
│  │ • data/chromadb/ (30 vector chunks)      │  │ • openai/gpt-oss-120b        │  │
│  │ • data/sources_manifest.json             │  │ • Rate Limiter: 30 RPM       │  │
│  │ • data/sessions/<session_id>.json        │  │ • Exponential Backoff Retry  │  │
│  └──────────────────────────────────────────┘  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
                                         ▲
                                         │ 3. Automated 10:00 AM IST Sync
┌────────────────────────────────────────┴─────────────────────────────────────────┐
│                      GITHUB ACTIONS (Phase 7 Daily Scheduler)                    │
│ • Runs daily at 10:00 AM IST (04:30 UTC): .github/workflows/daily_ingestion.yml  │
│ • Scrapes live Groww HTML, rebuilds ChromaDB, and triggers Railway deploy hook    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Decoupling Strategy: Streamlit to Client-Server

### Why Decouple?
Streamlit is an interactive rapid-prototyping framework built around stateful Python sessions and persistent WebSocket connections. While optimal for local development and internal tools, deploying Streamlit directly to **Vercel** is architecturally incompatible because:
1. **Serverless Limitations**: Vercel executes serverless functions with strict execution timeouts (10s on Hobby, 60s on Pro), whereas Streamlit requires a persistent, long-running daemon process.
2. **WebSocket Support**: Streamlit's UI updates depend on bi-directional WebSockets that cannot survive serverless cold starts.
3. **Heavy Python Runtimes**: Bundling PyTorch, SentenceTransformers, and ChromaDB into a serverless lambda violates Vercel's 50MB-250MB deployment size boundaries.

### The Decoupled Solution
- **Railway** hosts the full Python runtime with containerized dependencies, persistent local disk storage for ChromaDB, and dedicated CPU/RAM for vector similarity searches.
- **Vercel** hosts a pure web frontend (zero Python dependency) that delivers the Groww design system with instant global asset caching.

---

## 4. Backend Deployment on Railway

### 4.1 API Architecture & FastAPI Endpoints

The backend will expose clean, typed REST endpoints through a new module `src/api/`:

```
src/api/
├── __init__.py
├── main.py            # FastAPI app initialization, middleware, CORS, lifespan
├── routes.py          # /api/chat, /api/schemes, /api/sessions, /health
└── schemas.py         # Pydantic request and response schemas
```

#### API Endpoint Specifications

| Method | Path | Description | Request Body | Response Body |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Health check for Railway load balancers | *None* | `{"status": "ok", "chunks_indexed": 30, "model": "openai/gpt-oss-120b"}` |
| `POST` | `/api/chat` | Main RAG inquiry pipeline | `{"query": str, "thread_id": Optional[str]}` | `ChatResponseSchema` (content, citation, refusal flag, updated date) |
| `GET` | `/api/schemes` | Fetch 5 canonical Groww schemes overview | *None* | `List[SchemeOverviewSchema]` |
| `GET` | `/api/sessions` | List active user threads sorted by recency | *None* | `List[ThreadMetadataSchema]` |
| `GET` | `/api/sessions/{id}`| Fetch complete message history for thread | *None* | `ThreadHistorySchema` |
| `DELETE`| `/api/sessions/{id}`| Delete conversation thread and session file| *None* | `{"status": "deleted", "thread_id": str}` |
| `POST` | `/api/admin/reindex`| Protected webhook to trigger ChromaDB refresh| `{"api_key": str, "force": bool}` | `{"status": "reindexed", "total_chunks": 30}` |

#### Implementation Draft: `src/api/schemas.py`
```python
from typing import List, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    thread_id: str
    query: str
    content: str
    citation_url: Optional[str] = None
    is_refusal: bool = False
    refusal_type: Optional[str] = None
    last_updated: str
    execution_time_ms: float

class SchemeSummary(BaseModel):
    scheme_id: str
    scheme_name: str
    category: str
    url: str
    nav: str
    expense_ratio: str
    exit_load: str
    fund_size: str
```

#### Implementation Draft: `src/api/main.py`
```python
import os
import time
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.config import config
from src.api.schemas import ChatRequest, ChatResponse, SchemeSummary
from src.generation.llm_client import RAGPipelineOrchestrator
from src.state.session_manager import SessionManager
from src.utils.logger import get_logger

logger = get_logger("src.api.main")
app = FastAPI(title="HDFC Mutual Fund FAQ RAG API", version="1.0.0")

# Allow Vercel frontend and local development
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = RAGPipelineOrchestrator()
session_manager = SessionManager(storage_dir=config.session_persist_path)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "chromadb_collection": config.chroma_collection_name,
        "embedding_model": config.embedding_model_name,
        "llm_model": config.groq_model,
        "timestamp": time.time(),
    }

@app.post("/api/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest):
    start_time = time.time()
    thread_id = request.thread_id or session_manager.create_thread(title="New Conversation")
    
    # Execute RAG Pipeline
    result = orchestrator.answer_query(request.query)
    
    # Save to session history
    session_manager.add_message(thread_id, "user", request.query)
    session_manager.add_message(
        thread_id,
        "assistant",
        result.content,
        metadata={"citation_url": str(result.citation_url) if result.citation_url else None}
    )
    
    elapsed_ms = (time.time() - start_time) * 1000
    return ChatResponse(
        thread_id=thread_id,
        query=request.query,
        content=result.content,
        citation_url=str(result.citation_url) if result.citation_url else None,
        is_refusal=result.is_refusal,
        refusal_type=result.refusal_type,
        last_updated=result.last_updated,
        execution_time_ms=elapsed_ms,
    )
```

---

### 4.2 Railway Dockerfile & Build Configuration

To run reliably on Railway with minimal container size, we use a lightweight `python:3.11-slim` base image with build caching and non-root execution permissions.

#### `Dockerfile`
```dockerfile
# ==============================================================================
# Production Dockerfile for Mutual Fund FAQ RAG Backend (Railway)
# ==============================================================================
FROM python:3.11-slim as base

# Prevent Python from writing .pyc files and force unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn[standard]

# Copy application source code and corpus data
COPY src/ /app/src/
COPY data/ /app/data/

# Pre-download SentenceTransformer model into container cache to prevent runtime cold start delays
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Ensure data directories exist
RUN mkdir -p /app/data/chromadb /app/data/sessions /app/data/raw /app/data/processed

# Non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose dynamic Railway PORT
EXPOSE ${PORT}

# Run FastAPI via Uvicorn
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT} --workers 2"]
```

#### `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300
  }
}
```

---

### 4.3 Persistent Storage & Volume Strategy

ChromaDB uses persistent SQLite and HNSW vector index files stored in `data/chromadb/`. In a standard ephemeral container, container restarts would purge any dynamically indexed data or user sessions.

**Railway Persistent Volume Configuration**:
1. In the Railway project dashboard, attach a **Persistent Volume** to the backend service.
2. Set the volume mount path to:
   ```
   /app/data
   ```
3. Set the volume size to **5 GB** (plenty for 30 vector chunks and tens of thousands of session JSON threads).
4. Container startup verification: If `/app/data/chromadb` is empty on a fresh volume, the service runs `python -m src.ingestion.indexer` during initial container initialization.

---

### 4.4 Railway Environment Variables

Configure these variables in the **Railway Dashboard > Service Settings > Variables**:

```ini
# Production Environment Flag
ENVIRONMENT=production
LOG_LEVEL=INFO

# Groq Cloud API Credentials (Required)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
LLM_TEMPERATURE=0.0
LLM_TOP_P=0.1
LLM_MAX_OUTPUT_TOKENS=600

# Persistent Storage Paths (Mapped to Railway Volume)
CHROMA_PERSIST_DIRECTORY=/app/data/chromadb
CHROMA_COLLECTION_NAME=hdfc_mutual_fund_facts
SESSION_PERSIST_PATH=/app/data/sessions/

# Vector Retrieval Tuning
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
RETRIEVAL_TOP_K=3
SIMILARITY_THRESHOLD=0.65
USE_RERANKER=false

# Regulatory Guardrails & Output Formatting
MAX_OUTPUT_SENTENCES=3
ENFORCE_SINGLE_CITATION=true
SEBI_DISCLAIMER_TEXT="Facts-only. No investment advice."

# Allowed CORS Origins (Vercel Production & Preview URLs)
ALLOWED_ORIGINS=https://*.vercel.app,https://your-custom-domain.com,http://localhost:3000
```

---

## 5. Frontend Deployment on Vercel

### 5.1 Frontend Tech Stack Options

We recommend two clear pathways for the Vercel frontend:

| Option | Technology | Pros | Best For |
| :--- | :--- | :--- | :--- |
| **Option A (Recommended)** | **Next.js 14 (App Router) + React + TailwindCSS** | Native Vercel integration, SSR for fast initial loads, easy state management, instant preview deployments. | Production scalability, long-term maintenance, rich micro-interactions. |
| **Option B (Zero-Build Fast Track)** | **Static Single-Page Application (HTML5 / Vanilla JS / CSS)** | Directly deploys the tested `stitch/` code with zero framework overhead; instant build time (<5s). | Immediate one-click deployment with exact visual parity to Stitch prototypes. |

---

### 5.2 Vercel Configuration & Reverse Proxy

To prevent CORS issues between the Vercel frontend domain (`https://mutualfund-rag.vercel.app`) and Railway backend domain (`https://mutualfund-rag-production.up.railway.app`), configure a **Vercel Reverse Proxy** in `vercel.json`.

With this configuration:
- Frontend requests `fetch('/api/chat')`.
- Vercel routes `/api/*` directly to Railway over internal HTTPS.
- Zero CORS errors, and browser cookies/headers pass smoothly.

#### `vercel.json`
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://mutualfund-rag-backend.up.railway.app/api/:path*"
    },
    {
      "source": "/health",
      "destination": "https://mutualfund-rag-backend.up.railway.app/health"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

---

### 5.3 Groww Obsidian Emerald UI Integration

The frontend faithfully adheres to the design specification in [`stitch/obsidian_emerald/DESIGN.md`](file:///c:/Projects/Mutualfund_RAG/stitch/obsidian_emerald/DESIGN.md) and HTML designs in `stitch/`:

1. **Color Palette Tokens**:
   - Background Canvas: `#0E1015`
   - Card Surfaces: `#161922`
   - Borders: `#222735`
   - Groww Primary Accent: `#00D09C` (Hover: `#33DAAF`)
   - Refusal Alert Card: `#FF5252` border / `rgba(255, 82, 82, 0.08)` background.
2. **Key Layout Elements**:
   - **Fixed Header**: Groww logo, HDFC Facts Assistant title, and always-visible SEBI compliance disclaimer.
   - **Scheme Snapshot Carousel**: Real-time NAV, TER, Exit Load, and Fund Size cards for the 5 canonical HDFC schemes.
   - **Quick Action Chips**: "What is HDFC Mid-Cap exit load?", "Check Silver ETF TER", "Minimum SIP for Small Cap", "Lock-in period for Multi Cap".
   - **Chat Feed**:
     - Right-aligned dark-slate user bubbles.
     - Left-aligned obsidian assistant cards with verified citation buttons linking strictly to canonical Groww URLs.
     - Amber refusal cards with educational AMFI and SEBI links whenever investment advice is attempted.
   - **Bottom Input Dock**: Clean input pill with placeholder and auto-expanding textarea with strict overflow boundaries.

---

### 5.4 Vercel Environment Variables

Set in **Vercel Dashboard > Project Settings > Environment Variables**:

```ini
# Backend API Base URL (Used during build and runtime)
NEXT_PUBLIC_API_BASE_URL=https://mutualfund-rag-backend.up.railway.app

# Optional Custom Brand Identity
NEXT_PUBLIC_APP_TITLE="Groww | HDFC Mutual Fund Facts Assistant"
```

---

## 6. Daily Ingestion Scheduler CI/CD Integration

In Phase 7, we implemented the automated GitHub Actions workflow [.github/workflows/daily_ingestion.yml](file:///c:/Projects/Mutualfund_RAG/.github/workflows/daily_ingestion.yml) running daily at **10:00 AM IST (04:30 UTC)**.

### Connecting Phase 7 to Railway
When data is updated on GitHub Actions, the deployed Railway instance needs to reflect the new data. We achieve this with two simple integration steps:

```
[GitHub Actions (Daily 10:00 AM IST)]
           │
           ├─ 1. Crawl Groww URLs & Update data/sources_manifest.json
           ├─ 2. Run Re-Indexing & Verify pytest regression suite
           ├─ 3. Commit updated manifest to GitHub
           │
           ▼
[Trigger Railway Deploy Webhook]
   curl -X POST https://backboard.railway.app/webhooks/v1/deploy/...
           │
           ▼
[Railway Auto-Redeploys Container]
   - Pulls latest commit with updated manifest
   - Refreshes ChromaDB collection with zero downtime
```

#### GitHub Actions Workflow Enhancement
Add a deployment step at the end of [.github/workflows/daily_ingestion.yml](file:///c:/Projects/Mutualfund_RAG/.github/workflows/daily_ingestion.yml):

```yaml
      - name: Trigger Railway Production Deployment
        if: success()
        run: |
          if [ -n "${{ secrets.RAILWAY_DEPLOY_WEBHOOK_URL }}" ]; then
            echo "Notifying Railway of fresh mutual fund data sync..."
            curl -f -X POST "${{ secrets.RAILWAY_DEPLOY_WEBHOOK_URL }}"
          else
            echo "RAILWAY_DEPLOY_WEBHOOK_URL not configured. Skipping deploy trigger."
          fi
```

---

## 7. Step-by-Step Implementation & Rollout Plan

```
PHASE D1                PHASE D2                PHASE D3                PHASE D4                PHASE D5
───────────────         ───────────────         ───────────────         ───────────────         ───────────────
FastAPI Backend         Railway Container       Vercel Frontend         CORS & Reverse          E2E Verification
Implementation          & Volume Deploy         Deployment              Proxy Setup             & Go-Live
  • src/api/ routes       • Dockerfile            • Next.js/SPA setup     • vercel.json rewrite   • 216 tests pass
  • Pydantic schemas      • Volume: /app/data     • Stitch UI port        • SSL & Domain config   • Health check OK
  • Local tests pass      • Healthcheck 200       • API Client wireup     • Zero CORS errors      • Golden queries
```

---

### Phase D1: Backend API Scaffold & FastAPI Layer

1. **Create API directory**:
   - Create `src/api/__init__.py`, `src/api/main.py`, `src/api/routes.py`, `src/api/schemas.py`.
2. **Add FastAPI dependencies to `requirements.txt`**:
   - `fastapi>=0.110.0`
   - `uvicorn[standard]>=0.28.0`
3. **Write Unit Tests for API Endpoints**:
   - Create `tests/test_api_endpoints.py`:
     - Test `GET /health` returns status `healthy`.
     - Test `POST /api/chat` with factual query returns 3 sentences, 1 citation, and 200 OK.
     - Test `POST /api/chat` with advisory query ("Should I invest?") returns `is_refusal: true`.
     - Test `POST /api/chat` with PII query returns PII block.
     - Test `GET /api/schemes` returns 5 schemes.
4. **Local Verification**:
   ```bash
   uvicorn src.api.main:app --port 8000 --reload
   curl http://localhost:8000/health
   ```

---

### Phase D2: Containerization & Railway Provisioning

1. **Create Docker artifacts**:
   - Create `Dockerfile` (optimized multi-stage build).
   - Create `.dockerignore` (exclude `venv/`, `.git/`, `.pytest_cache/`, `tests/`).
   - Create `railway.json`.
2. **Test Docker build locally**:
   ```bash
   docker build -t mutualfund-rag-backend:latest .
   docker run -p 8000:8000 --env-file .env mutualfund-rag-backend:latest
   curl http://localhost:8000/health
   ```
3. **Create Project on Railway**:
   - Log in to [Railway.app](https://railway.app/).
   - Click **New Project** > **Deploy from GitHub repo** > Select `Mutualfund_RAG`.
4. **Attach Persistent Volume**:
   - In the service settings, click **Add Volume**.
   - Mount Path: `/app/data`.
   - Size: `5 GB`.
5. **Configure Environment Variables**:
   - Add `GROQ_API_KEY`, `CHROMA_PERSIST_DIRECTORY=/app/data/chromadb`, etc.
6. **Generate Domain**:
   - In Settings > Networking, click **Generate Domain** (e.g., `mutualfund-rag-backend.up.railway.app`).
   - Verify health check: `https://mutualfund-rag-backend.up.railway.app/health`.

---

### Phase D3: Frontend Client Packaging & Vercel Setup

1. **Option Selection**:
   - If using **Option A (Next.js)**: Initialize client under `frontend/` with React, TailwindCSS, and Lucide icons using the Stitch design tokens.
   - If using **Option B (Static SPA)**: Create `frontend/` or root `public/` using the HTML/CSS from `stitch/code.html` with an asynchronous `fetch()` API client module.
2. **API Client Implementation**:
   - Implements `queryAssistant(query, threadId)` targeting `/api/chat`.
   - Implements `getSchemesOverview()` targeting `/api/schemes`.
   - Implements thread switching and local storage backup.
3. **Create Project on Vercel**:
   - Log in to [Vercel](https://vercel.com/).
   - Click **Add New...** > **Project** > Import the repository.
   - Set Root Directory to `frontend` (or project root if static SPA).
4. **Set Environment Variables**:
   - Add `NEXT_PUBLIC_API_BASE_URL`.

---

### Phase D4: Networking, CORS & Reverse Proxy Wiring

1. **Configure `vercel.json` rewrites**:
   - Point `/api/:path*` to the Railway production URL.
2. **Update Railway CORS variables**:
   - Add your newly assigned Vercel URL to `ALLOWED_ORIGINS` in Railway settings.
3. **Verify Network Connectivity**:
   - In browser console on the Vercel URL, run:
     ```javascript
     fetch('/api/chat', {
       method: 'POST',
       headers: {'Content-Type': 'application/json'},
       body: JSON.stringify({query: 'What is the expense ratio of HDFC Mid Cap?'})
     }).then(r => r.json()).then(console.log);
     ```
   - Must return 200 OK with compliant JSON response.

---

### Phase D5: End-to-End Verification & Health Checks

1. **Run Golden Test Suite against Live Deployment**:
   - Send 5 factual queries (NAV, TER, Exit Load, Benchmark, SIP).
   - Send 2 advisory queries (verify polite refusal card).
   - Send 1 PII query (verify interception).
2. **Check Latency**:
   - TTFB < 200ms on Vercel.
   - Total chat inference roundtrip < 2.5s on Railway + Groq.

---

## 8. Acceptance Gate & Smoke Test Matrix

Before declaring the deployment live, the following automated and manual checks must pass:

| Gate # | Category | Verification Method | Pass Condition | Status |
| :--- | :--- | :--- | :--- | :--- |
| **G1** | Backend Health | `GET https://<railway-url>/health` | Status `healthy`, 30 chunks indexed | Pending Deploy |
| **G2** | Reverse Proxy | `GET https://<vercel-url>/health` | Proxies to Railway and returns 200 OK | Pending Deploy |
| **G3** | Factual Query | Send query: "What is the exit load of HDFC Small Cap?" | ≤ 3 sentences, 1 Groww citation badge, 200 OK | Pending Deploy |
| **G4** | Advisory Gate | Send query: "Should I buy HDFC Mid-Cap?" | Refusal response returned, AMFI link present | Pending Deploy |
| **G5** | PII Gate | Send query with dummy PAN `ABCDE1234F` | PII redactor blocks query before Groq call | Pending Deploy |
| **G6** | Persistence | Create thread, refresh browser | Thread history persists from Railway volume | Pending Deploy |
| **G7** | Design System | Inspect UI in browser | Obsidian Emerald theme (#121212, #00D09C) rendered | Pending Deploy |
| **G8** | Test Suite | `pytest tests/ -v` | All 216+ automated tests passing | ✅ 216 Passed |

---

## 9. Cost, Sizing & Resource Allocation

Both Railway and Vercel offer generous free/hobby tiers that completely accommodate this application:

| Platform | Tier | Monthly Cost | Included Resources | Application Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Railway** | Hobby / Trial | ~$5 / month (Usage-based) | 512MB–8GB RAM, 1–8 vCPUs, 10GB persistent storage | ~300MB RAM, 0.2 vCPU, 1GB disk |
| **Vercel** | Hobby | **$0 (Free)** | 100GB bandwidth, unlimited preview deployments, SSL | ~5GB bandwidth, static asset caching |
| **Groq Cloud**| Free Tier | **$0 (Free)** | 30 RPM, 8K TPM, 1K RPD, 200K TPD (`openai/gpt-oss-120b`) | Well within daily development & user query quotas |
| **Total** | — | **~$5 / month** | Full multi-cloud production deployment | Low operational overhead |

---

## 10. Runbooks, Troubleshooting & Disaster Recovery

### Issue 1: ChromaDB Returns 0 Chunks After Railway Redeployment
- **Cause**: Persistent Volume was either not mounted or mounted to an incorrect path.
- **Fix**:
  1. Verify Volume Mount Path in Railway dashboard is strictly set to `/app/data`.
  2. Open Railway terminal for the service and run:
     ```bash
     python -m src.ingestion.indexer --rebuild
     ```
  3. Verify collection count: `python -c "import chromadb; c=chromadb.PersistentClient('/app/data/chromadb'); print(c.get_collection('hdfc_mutual_fund_facts').count())"` (must output `30`).

### Issue 2: CORS Blocked when Querying Backend
- **Cause**: Browser blocked cross-origin request because Vercel reverse proxy rewrite is missing or Railway `ALLOWED_ORIGINS` does not include the Vercel domain.
- **Fix**:
  1. Ensure `vercel.json` contains the `/api/:path*` rewrite to Railway.
  2. In Railway Dashboard, set `ALLOWED_ORIGINS=*` temporarily to diagnose, then lock down to `https://*.vercel.app`.

### Issue 3: Groq Rate Limit (`429 Too Many Requests`)
- **Cause**: Spike in concurrent queries exceeded 30 RPM or 8K TPM.
- **Fix**: The built-in client-side rate limiter in [src/generation/llm_client.py](file:///c:/Projects/Mutualfund_RAG/src/generation/llm_client.py) will automatically execute exponential backoff up to 3 retries. If persistent, upgrade to Groq Developer tier or queue queries.

### Issue 4: Cold Start Latency
- **Cause**: Docker container downloading `all-MiniLM-L6-v2` at startup.
- **Fix**: Ensure the `RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"` step is preserved in the Dockerfile so the weights are baked into the container image layer.

---

> 🔗 **Related Documentation**:
> - Implementation Plan: [`Docs/implementation-plan.md`](file:///c:/Projects/Mutualfund_RAG/Docs/implementation-plan.md)
> - Architecture Specification: [`Docs/architecture.md`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md)
> - Design System Blueprint: [`stitch/obsidian_emerald/DESIGN.md`](file:///c:/Projects/Mutualfund_RAG/stitch/obsidian_emerald/DESIGN.md)
> - Daily Ingestion Workflow: [`.github/workflows/daily_ingestion.yml`](file:///c:/Projects/Mutualfund_RAG/.github/workflows/daily_ingestion.yml)
