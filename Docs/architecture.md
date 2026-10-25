# 🏗️ Architecture Document: Mutual Fund FAQ Assistant (Facts-Only Q&A)

> **Context**: Groww-Inspired Mutual Fund Facts Assistant  
> **AMC Focus**: HDFC Mutual Fund — 5 Curated Diverse Schemes  
> **Core Tenet**: Strict SEBI RIA compliance · Zero hallucination · Verifiable citations · Deterministic advisory refusals

---

## 📖 Table of Contents

1. [Executive Summary & Architectural Goals](#1-executive-summary--architectural-goals)
2. [High-Level System Architecture](#2-high-level-system-architecture)
3. [Technology Stack & Selection Rationale](#3-technology-stack--selection-rationale)
4. [Project Directory Layout](#4-project-directory-layout)
5. [End-to-End Data & Query Flow](#5-end-to-end-data--query-flow)
6. [Detailed Subsystem Specifications](#6-detailed-subsystem-specifications)
   - [6.1 Document Ingestion & Corpus Pipeline](#61-document-ingestion--corpus-pipeline)
   - [6.2 Chunking Strategy & Metadata Schema](#62-chunking-strategy--metadata-schema)
   - [6.3 Embedding & Vector Storage Layer](#63-embedding--vector-storage-layer)
   - [6.4 Guardrails & Refusal Classifier Engine](#64-guardrails--refusal-classifier-engine)
   - [6.5 Retrieval & Context Assembly Engine](#65-retrieval--context-assembly-engine)
   - [6.6 LLM Generation & Strict Output Formatter](#66-llm-generation--strict-output-formatter)
   - [6.7 Multi-Thread Session & State Management](#67-multi-thread-session--state-management)
7. [Data Models & Schema Specifications](#7-data-models--schema-specifications)
8. [Prompt Engineering & Compliance System Prompts](#8-prompt-engineering--compliance-system-prompts)
9. [UI Architecture & Groww Design System](#9-ui-architecture--groww-design-system)
10. [Security, Privacy (PII) & SEBI Regulatory Safeguards](#10-security-privacy-pii--sebi-regulatory-safeguards)
11. [Error Handling, Edge Cases & Fallback Strategy](#11-error-handling-edge-cases--fallback-strategy)
12. [Evaluation, Observability & Validation Framework](#12-evaluation-observability--validation-framework)
13. [Deployment, Environment & Configuration Architecture](#13-deployment-environment--configuration-architecture)

---

## 1. Executive Summary & Architectural Goals

The **Mutual Fund FAQ Assistant** is a lightweight, enterprise-grade **Retrieval-Augmented Generation (RAG)** system engineered to answer factual, verifiable queries regarding mutual fund schemes — without ever crossing the threshold into financial advice. Built around **5 curated HDFC Mutual Fund** schemes within a **Groww** platform context, the architecture resolves three fundamental challenges of applying Generative AI to regulated financial products:

### The Three Architectural Pillars

| Pillar | Challenge | How This Architecture Addresses It |
| :--- | :--- | :--- |
| **Deterministic Regulatory Compliance** | Unregulated AI assistants risk providing implicit investment recommendations, violating SEBI Investment Adviser Regulations, 2013. | A dual-stage safety gate: pre-retrieval **query intent classifier** (regex + lightweight LLM gate) identifies advisory intent, and a post-generation **compliance validator** ensures no comparative or predictive language leaks through. Target: **100% refusal rate** on advisory queries. |
| **Zero-Hallucination Grounding** | Factsheets, KIMs, and SIDs contain dense financial figures (expense ratios, exit load tiers, lock-in periods). Standard LLMs hallucinate these freely. | Table-aware PDF parsing (`pdfplumber`) preserves the structural integrity of financial tables. Scheme-scoped **metadata filtering** in ChromaDB restricts retrieval to the exact fund's documents. LLM invoked at `temperature=0.0` with explicit grounding instructions. |
| **Strict Structural Guarantees** | Financial answers must be concise, citable, and datable — not open-ended prose. | Every response passes through a machine-enforced **Output Contract Validator**: max 3 sentences, exactly 1 authoritative source URL, and a mandatory `Last updated from sources: <date>` footer. Violations are auto-corrected before display. |

---

## 2. High-Level System Architecture

The system follows a **modular, layered pipeline architecture** with strict separation between ingestion (offline), guardrails, retrieval, generation, and presentation:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER (Groww Dark Theme)                              │
│  ┌─────────────────────┐  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 💬 Thread Sidebar    │  │  🤖 Chat Area: Welcome + Chips + Message History + Input     │  │
│  │ [+ New Thread]       │  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │ • HDFC Mid-Cap Q's   │  │  │ 🏷️ Disclaimer: "Facts-only. No investment advice."     │ │  │
│  │ • Silver ETF Info    │  │  └─────────────────────────────────────────────────────────┘ │  │
│  │ • CAS Statement      │  │  [Chip 1] [Chip 2] [Chip 3]                                 │  │
│  └─────────────────────┘  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────┬──────────────────────────────────────────────────┘
                                           │ User Query
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                         GUARDRAILS LAYER (Pre-Retrieval Safety Gates)                        │
│                                                                                              │
│  ┌──────────────────────────────┐     ┌────────────────────────────────────────────────────┐ │
│  │ 🛡️ GATE 1: PII Interceptor   │────▶│ 🧠 GATE 2: Query Intent Classifier                │ │
│  │ Blocks PAN, Aadhaar, Folio,  │     │ Regex Fast-Path + LLM Intent Fallback             │ │
│  │ OTP, Phone, Email            │     │ ┌──────────────┐    ┌──────────────────────────┐   │ │
│  └──────────────────────────────┘     │ │ ADVISORY     │    │ FACTUAL / OPERATIONAL    │   │ │
│                                       │ │ → Refuse     │    │ → Proceed to Retrieval   │   │ │
│                                       │ └──────┬───────┘    └──────────┬───────────────┘   │ │
│                                       └────────┼───────────────────────┼────────────────────┘ │
└────────────────────────────────────────────────┼───────────────────────┼──────────────────────┘
                                                 │                       │
                    ┌────────────────────────────┘                       │
                    ▼                                                    ▼
┌────────────────────────────────────┐   ┌─────────────────────────────────────────────────────┐
│     REFUSAL ENGINE                 │   │              RETRIEVAL & CONTEXT ASSEMBLY LAYER      │
│ • Polite facts-only explanation    │   │                                                      │
│ • AMFI / SEBI educational link     │   │  1. Scheme & Topic Entity Extractor                  │
│ • Returns directly to UI           │   │     ("hdfc_mid_cap" + "exit load")                   │
└────────────────────────────────────┘   │  2. ChromaDB Metadata-Filtered Vector Search         │
                                         │     (scheme_id + doc_type pre-filter → cosine sim)    │
                                         │  3. Top-K Context Chunk Assembly (K=3, with source)   │
                                         └───────────────────────┬─────────────────────────────┘
                                                                 │
                                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                     GENERATION & OUTPUT CONTRACT ENFORCEMENT LAYER                           │
│                                                                                              │
│  1. Strict Prompt Assembly: [System Prompt + Grounded Context Chunks + User Query]           │
│  2. LLM Inference: Google Gemini Flash (temperature=0.0, top_p=0.1)                          │
│  3. Output Contract Validator:                                                               │
│     ├── ✅ Rule 1: ≤ 3 sentences (enforced via sent_tokenize; truncates if exceeded)          │
│     ├── ✅ Rule 2: Exactly 1 authoritative citation URL (deduplicates or injects canonical)   │
│     └── ✅ Rule 3: Mandatory footer: "Last updated from sources: <YYYY-MM-DD>"               │
└──────────────────────────────────────────┬──────────────────────────────────────────────────┘
                                           │ Verified Compliant Answer
                                           ▼
                                    [Display on UI Card]


═══════════════════════════════════════════════════════════════════════════════════════════════
                               OFFLINE INGESTION PIPELINE
═══════════════════════════════════════════════════════════════════════════════════════════════

  ┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
  │ 📄 Raw Official Docs   │───▶│ 📊 Table-Aware Parser  │───▶│ ✂️ Semantic Chunker    │
  │ SID, KIM, Factsheets  │    │ pdfplumber + trafilat. │    │ 400-600 tok + metadata│
  │ AMFI/SEBI Guides      │    │ Preserves table struct │    │ scheme_id, doc_type,  │
  │ Help/FAQ Pages        │    │                        │    │ source_url, pub_date  │
  └───────────────────────┘    └───────────────────────┘    └──────────┬────────────┘
                                                                       │
                                                                       ▼
                                                            ┌───────────────────────┐
                                                            │ 📦 ChromaDB Indexer    │
                                                            │ all-MiniLM-L6-v2      │
                                                            │ Persistent collection │
                                                            └───────────────────────┘
```

---

## 3. Technology Stack & Selection Rationale

| Layer | Technology | Version | Why This Choice |
| :--- | :--- | :--- | :--- |
| **Language** | **Python** | `3.10+` | Dominant AI/ML ecosystem; first-class support for LangChain, ChromaDB, PDF parsing, Pydantic typing. |
| **LLM Inference** | **Google Gemini Flash** | `gemini-1.5-flash` or `gemini-2.0-flash` | Low latency (<1.2s TTFT), large context window (1M tokens), cost-effective, strong instruction-following for strict formatting. |
| **Embedding Model** | `sentence-transformers/all-MiniLM-L6-v2` | Latest | 384-dim embeddings, 80MB model, runs locally with zero network dependency. Alternatively `text-embedding-004` via Gemini API. |
| **Vector Database** | **ChromaDB** | `≥0.5.0` | Serverless embedded mode, native metadata filtering (`$and`, `$eq`, `$in`), zero-infrastructure local setup. |
| **PDF Extraction** | **pdfplumber** + **PyMuPDF** | Latest | `pdfplumber` excels at complex financial table extraction (expense ratio grids, exit load tiers). PyMuPDF handles raw text fallback. |
| **HTML Extraction** | **Trafilatura** | Latest | Removes navigation/ad boilerplate from AMC help pages; extracts clean article text. |
| **Orchestration** | **LangChain** (optional) or **Custom Pipeline** | Latest | Modular chain composition for retrieval → prompt → LLM → parse. Custom pipeline preferred for tighter control over output contract enforcement. |
| **Data Validation** | **Pydantic v2** | `≥2.0` | Strictly typed schemas for chunks, queries, responses, and sessions. Runtime validation of all data boundaries. |
| **Web UI** | **Streamlit** with custom CSS | Latest | Rapid prototyping, native `st.session_state` for multi-thread management, easy Groww-themed CSS injection. |
| **Intent Classifier** | **Regex Fast-Path + LLM Gate** | Internal | Hybrid: zero-latency regex catches obvious advisory keywords; ambiguous queries fall through to a fast LLM classifier call. |
| **Session Storage** | **SQLite** / **JSON** / `st.session_state` | — | Lightweight thread and message persistence without external database infrastructure. |
| **Testing** | **pytest** + **nltk** | Latest | `pytest` for unit/integration; `nltk.sent_tokenize` for automated sentence-count validation in output contract tests. |
| **Logging** | **Python `logging`** with structured JSON | Built-in | Audit trail for every query, intent classification decision, and retrieval result — critical for compliance traceability. |

---

## 4. Project Directory Layout

```
Mutualfund_RAG/
│
├── Docs/                                   # Project documentation
│   ├── problemstatement.txt                # Original raw requirements
│   ├── problemstatement.md                 # Comprehensive scope & Groww scheme URLs
│   ├── architecture.md                     # System architecture blueprint (THIS FILE)
│   ├── implementation-plan.md              # Phase-wise development roadmap
│   └── eval.md                             # Evaluation benchmarks & quality metrics
│
├── data/                                   # All data artifacts
│   ├── raw/                                # Downloaded official PDFs & HTML snapshots
│   │   ├── hdfc_mid_cap/                   # SID, KIM, Factsheet for Mid-Cap Fund
│   │   ├── hdfc_small_cap/                 # SID, KIM, Factsheet for Small Cap Fund
│   │   ├── hdfc_large_mid_cap/             # SID, KIM, Factsheet for Large & Mid Cap
│   │   ├── hdfc_silver_etf_fof/            # SID, KIM, Factsheet for Silver ETF FoF
│   │   ├── hdfc_multi_cap/                 # SID, KIM, Factsheet for Multi Cap Fund
│   │   └── common/                         # AMFI/SEBI guides, CAS download guides
│   ├── processed/                          # Clean extracted text & Markdown tables
│   ├── sources_manifest.json              # Canonical list of 15-25 URLs + SHA-256 hashes
│   └── chromadb/                           # Persistent ChromaDB vector store directory
│
├── src/                                    # Application source code
│   ├── __init__.py
│   ├── config.py                           # Centralized settings (Pydantic BaseSettings)
│   │
│   ├── ingestion/                          # OFFLINE: Corpus building pipeline
│   │   ├── __init__.py
│   │   ├── crawler.py                      # URL fetcher & PDF downloader with hash tracking
│   │   ├── pdf_parser.py                   # Table-aware PDF extraction via pdfplumber
│   │   ├── html_parser.py                  # Web page text extraction via Trafilatura
│   │   ├── chunker.py                      # Semantic + table-preserving chunking engine
│   │   └── indexer.py                      # ChromaDB embedding & indexing pipeline
│   │
│   ├── guardrails/                         # ONLINE: Pre-retrieval safety gates
│   │   ├── __init__.py
│   │   ├── pii_redactor.py                 # Regex interceptor for PAN, Aadhaar, Folio, OTP
│   │   ├── intent_classifier.py            # Factual vs. Advisory/Comparative query router
│   │   └── refusal_templates.py            # Polite refusal responses + AMFI/SEBI links
│   │
│   ├── retrieval/                          # ONLINE: Context search & assembly
│   │   ├── __init__.py
│   │   ├── entity_extractor.py             # Scheme name & financial topic identifier
│   │   ├── retriever.py                    # ChromaDB vector query with metadata pre-filters
│   │   └── reranker.py                     # Optional cross-encoder or RRF reranking
│   │
│   ├── generation/                         # ONLINE: LLM prompting & output enforcement
│   │   ├── __init__.py
│   │   ├── prompt_templates.py             # System prompts with strict formatting rules
│   │   ├── llm_client.py                   # Gemini API wrapper with retry & error handling
│   │   └── output_formatter.py             # Output Contract Validator (3 sent, 1 URL, date)
│   │
│   ├── state/                              # Multi-thread session management
│   │   ├── __init__.py
│   │   ├── session_manager.py              # Thread CRUD, switching, and message history
│   │   └── models.py                       # Pydantic schemas (Thread, Message, Chunk, etc.)
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py                       # Structured JSON logger for compliance audit trail
│
├── ui/                                     # User interface layer
│   ├── app.py                              # Streamlit main entrypoint
│   ├── components.py                       # Groww-themed cards, chips, citation badges
│   └── styles.css                          # Custom dark/light CSS design tokens
│
├── tests/                                  # Automated test suite
│   ├── test_guardrails.py                  # Advisory refusal & PII interception tests
│   ├── test_ingestion.py                   # PDF parsing & chunking correctness
│   ├── test_retrieval.py                   # Semantic retrieval & metadata filter accuracy
│   ├── test_output_contract.py             # Sentence count, citation, and date format
│   └── test_sessions.py                    # Multi-thread isolation & persistence
│
├── .env.example                            # Environment variable template
├── requirements.txt                        # Python dependencies
└── README.md                               # Setup, run, and usage instructions
```

---

## 5. End-to-End Data & Query Flow

### 5.1 Offline: Document Ingestion Pipeline

```mermaid
flowchart LR
    subgraph Sources ["Official Sources (HDFC AMC / AMFI / SEBI)"]
        SID["Scheme Information\nDocuments (SID)"]
        KIM["Key Information\nMemorandums (KIM)"]
        FS["Monthly Factsheets\n(Expense Ratios, AUM)"]
        FAQ["AMC Help & FAQ\nPages"]
        AMFI_SEBI["AMFI / SEBI\nRegulatory Guides"]
    end

    subgraph Crawl ["crawler.py"]
        Fetch["Download PDFs\n& Snapshot HTML"]
        Hash["Compute SHA-256\nfor Change Detection"]
    end

    subgraph Parse ["pdf_parser.py + html_parser.py"]
        TableExtract["Table-Aware\nPDF Extraction"]
        HTMLClean["Boilerplate-Free\nHTML Text"]
    end

    subgraph Chunk ["chunker.py"]
        Semantic["Semantic Chunking\n400-600 tokens"]
        MetaTag["Metadata Injection\nscheme_id, doc_type,\nsource_url, pub_date"]
    end

    subgraph Index ["indexer.py"]
        Embed["Generate Embeddings\nall-MiniLM-L6-v2"]
        Store["Upsert into\nChromaDB Collection"]
    end

    SID & KIM & FS & FAQ & AMFI_SEBI --> Fetch --> Hash
    Hash --> TableExtract & HTMLClean
    TableExtract & HTMLClean --> Semantic --> MetaTag --> Embed --> Store
```

### 5.2 Online: Query Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as Retail Investor
    participant UI as Groww UI
    participant PII as PII Interceptor
    participant IC as Intent Classifier
    participant RE as Refusal Engine
    participant EE as Entity Extractor
    participant VDB as ChromaDB
    participant PB as Prompt Builder
    participant LLM as Gemini Flash API
    participant OV as Output Validator

    User->>UI: "What is the exit load for HDFC Mid-Cap Fund?"
    UI->>PII: Scan for PAN / Aadhaar / Folio / OTP / Phone
    
    alt PII Detected
        PII-->>UI: ⛔ "Please don't share personal/account details."
    else Clean
        PII->>IC: Classify intent (Factual vs Advisory)
        
        alt Advisory Intent
            IC->>RE: Route to refusal
            RE-->>UI: Polite refusal + AMFI education link
        else Factual Intent
            IC->>EE: Extract scheme("hdfc_mid_cap") + topic("exit load")
            EE->>VDB: Vector search with metadata filter {scheme_id: "hdfc_mid_cap"}
            VDB-->>EE: Top-3 relevant chunks (KIM table rows)
            EE->>PB: Assemble [System Prompt + Context + Query]
            PB->>LLM: Invoke Gemini (temp=0.0, top_p=0.1)
            LLM-->>OV: Raw response text
            
            OV->>OV: Validate: ≤3 sentences? 1 URL? Date footer?
            alt All Invariants Pass
                OV-->>UI: ✅ Compliant response
            else Invariant Violation
                OV->>OV: Auto-fix: truncate sentences / inject URL / append date
                OV-->>UI: ✅ Normalized compliant response
            end
            
            UI-->>User: Answer card + citation badge + timestamp footer
        end
    end
```

---

## 6. Detailed Subsystem Specifications

### 6.1 Document Ingestion & Corpus Pipeline

The corpus strictly ingests **official statutory documents** for the 5 selected HDFC schemes:

| # | Scheme | `scheme_id` | Groww Reference URL | Documents to Ingest |
| :--- | :--- | :--- | :--- | :--- |
| 1 | HDFC Mid-Cap Opportunities Fund (Direct - Growth) | `hdfc_mid_cap` | [Groww Link](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth) | SID, KIM, Factsheet |
| 2 | HDFC Small Cap Fund (Direct - Growth) | `hdfc_small_cap` | [Groww Link](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth) | SID, KIM, Factsheet |
| 3 | HDFC Large and Mid Cap Fund (Direct - Growth) | `hdfc_large_mid_cap` | [Groww Link](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) | SID, KIM, Factsheet |
| 4 | HDFC Silver ETF Fund of Fund (Direct - Growth) | `hdfc_silver_etf_fof` | [Groww Link](https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth) | SID, KIM, Factsheet |
| 5 | HDFC Multi Cap Fund (Direct - Growth) | `hdfc_multi_cap` | [Groww Link](https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth) | SID, KIM, Factsheet |

**Cross-Scheme Documents**: AMFI category definitions, SEBI Riskometer guidelines, CAS/Capital Gains statement download guides.

#### `sources_manifest.json` Schema:

```json
{
  "manifest_version": "1.0",
  "last_updated": "2026-10-25",
  "sources": [
    {
      "url": "https://www.hdfcfund.com/...",
      "scheme_id": "hdfc_mid_cap",
      "doc_type": "KIM",
      "format": "pdf",
      "sha256": "a1b2c3...",
      "download_path": "data/raw/hdfc_mid_cap/kim.pdf"
    }
  ]
}
```

#### `crawler.py` Responsibilities:
1. Read `sources_manifest.json` for the canonical URL list.
2. Download each PDF/HTML page to `data/raw/<scheme_id>/`.
3. Compute SHA-256 hash of each file → compare against previous manifest to detect **document updates** (re-index only changed files).
4. Log all downloads with timestamps for audit.

#### `pdf_parser.py` — Table-Aware Extraction:
Financial documents pack critical data into tables. Standard text extraction flattens these into unusable strings.

```python
# Example: pdfplumber table extraction
import pdfplumber

def extract_tables_as_markdown(pdf_path: str) -> list[dict]:
    """Extract tables from PDF and convert to Markdown format."""
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            for table in page.extract_tables():
                # Convert to Markdown table
                header = "| " + " | ".join(str(c) for c in table[0]) + " |"
                separator = "| " + " | ".join("---" for _ in table[0]) + " |"
                rows = "\n".join(
                    "| " + " | ".join(str(c) for c in row) + " |"
                    for row in table[1:]
                )
                md_table = f"{header}\n{separator}\n{rows}"
                tables.append({
                    "content": md_table,
                    "page": page_num,
                    "type": "table"
                })
    return tables
```

---

### 6.2 Chunking Strategy & Metadata Schema

Naive character-level splitting destroys financial table integrity and separates conditions from their values. This system uses **table-aware semantic chunking**.

#### Chunking Rules:

| Parameter | Value | Rationale |
| :--- | :--- | :--- |
| **Chunk Size** | 400–600 tokens | Optimal for factual QA — dense enough for context, short enough to avoid noise dilution. |
| **Overlap** | 100 tokens | Preserves cross-boundary context (e.g., a condition stated at end of one paragraph, value in next). |
| **Table Handling** | Atomic if ≤ 500 tokens | Financial tables (exit load tiers, expense ratios) are kept intact as single chunks. If a table exceeds 500 tokens, split row-wise with **header replicated** in every sub-chunk. |
| **Section Headers** | Preserved | Each chunk retains its parent document section heading for retrieval context. |

#### Chunk Metadata Schema:

Every chunk stored in ChromaDB carries the following metadata, enabling precise **pre-retrieval filtering**:

```python
chunk_metadata = {
    "chunk_id": "hdfc_mid_cap_kim_003",         # Unique identifier
    "scheme_id": "hdfc_mid_cap",                 # Filter key: which fund
    "scheme_name": "HDFC Mid-Cap Opportunities Fund",
    "category": "Equity: Mid Cap",
    "doc_type": "KIM",                           # Filter key: SID | KIM | Factsheet | FAQ | Guide
    "source_url": "https://www.hdfcfund.com/...", # Canonical citation URL
    "groww_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "publish_date": "2026-09-30",                # For freshness footer
    "section": "Exit Load and Redemption Terms",  # Human-readable section
    "content_type": "table",                     # "table" | "text" | "list"
    "page_number": 4
}
```

---

### 6.3 Embedding & Vector Storage Layer

#### ChromaDB Configuration:

```python
import chromadb
from chromadb.utils import embedding_functions

# Initialize persistent client
client = chromadb.PersistentClient(path="data/chromadb")

# Embedding function
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Create or get collection
collection = client.get_or_create_collection(
    name="hdfc_mutual_fund_facts",
    embedding_function=ef,
    metadata={"hnsw:space": "cosine"}  # Cosine similarity
)
```

#### Metadata-Filtered Query Pattern:

The retriever never searches the entire corpus blindly. If the user mentions a specific scheme, the query is **pre-filtered by `scheme_id`** before vector similarity computation:

```python
results = collection.query(
    query_texts=["What is the exit load?"],
    n_results=3,
    where={
        "$and": [
            {"scheme_id": {"$eq": "hdfc_mid_cap"}},
            {"doc_type": {"$in": ["KIM", "SID", "Factsheet"]}}
        ]
    },
    include=["documents", "metadatas", "distances"]
)
```

#### Embedding Model Comparison:

| Model | Dimensions | Size | Latency | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `all-MiniLM-L6-v2` | 384 | 80 MB | ~5ms/query | Local, zero network dependency. Recommended for dev. |
| `text-embedding-004` (Gemini) | 768 | API | ~100ms/query | Higher quality, requires API key. Recommended for prod. |

---

### 6.4 Guardrails & Refusal Classifier Engine

The system implements a **Two-Tiered Safety Gate** that intercepts queries before they reach the retrieval pipeline:

#### Gate 1: PII Redaction Interceptor (`pii_redactor.py`)

Blocks queries containing any Indian financial PII using compiled regex patterns:

```python
import re
from typing import Optional

PII_PATTERNS = {
    "PAN": re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'),
    "Aadhaar": re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
    "Phone": re.compile(r'\b(?:\+91[\s-]?)?[6-9]\d{9}\b'),
    "Email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "Folio": re.compile(r'\b(?:folio[\s:#]*)\d{5,15}\b', re.IGNORECASE),
    "Account": re.compile(r'\b\d{9,18}\b'),  # Bank account numbers
}

def detect_pii(query: str) -> Optional[str]:
    """Returns the PII type detected, or None if clean."""
    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(query):
            return pii_type
    return None
```

#### Gate 2: Query Intent Classifier (`intent_classifier.py`)

A **hybrid classification** approach balancing latency and accuracy:

**Stage A — Regex Fast-Path** (< 1ms): Catches obvious advisory patterns immediately.
```python
ADVISORY_PATTERNS = [
    r'\bshould\s+i\s+(invest|buy|sell|switch|redeem)\b',
    r'\bwhich\s+(fund|scheme|one)\s+is\s+(better|best|good)\b',
    r'\brecommend\b', r'\bsuggestion\b', r'\badvice\b',
    r'\bexpected\s+return\b', r'\bfuture\s+(performance|growth|return)\b',
    r'\bwill\s+(this|the)\s+fund\s+(grow|rise|fall)\b',
    r'\bcompare\b.*\bfund\b',
]
```

**Stage B — LLM Intent Gate** (fallback for ambiguous queries): A fast, cheap Gemini call with a structured output asking for a single-word classification: `FACTUAL` or `ADVISORY`.

#### Refusal Response Template:

```python
REFUSAL_RESPONSE = (
    "I'm designed to provide only verified factual information about "
    "HDFC Mutual Fund schemes — such as expense ratios, exit loads, SIP "
    "minimums, and regulatory terms. I cannot offer investment advice, "
    "fund comparisons, or return predictions.\n\n"
    "For guidance on evaluating mutual funds, please visit "
    "[AMFI - Mutual Funds Sahi Hai](https://www.amfiindia.com/investor-corner/knowledge-center).\n\n"
    "*Last updated from sources: {date}*"
)
```

---

### 6.5 Retrieval & Context Assembly Engine

#### Step 1: Entity Extraction (`entity_extractor.py`)

Maps natural language fund references to canonical `scheme_id` values:

```python
SCHEME_ALIASES = {
    "hdfc_mid_cap": [
        "mid cap", "mid-cap", "midcap", "mid cap opportunities",
        "hdfc mid cap", "hdfc mid-cap", "hdfc midcap"
    ],
    "hdfc_small_cap": [
        "small cap", "small-cap", "smallcap", "hdfc small cap"
    ],
    "hdfc_large_mid_cap": [
        "large cap", "large-cap", "largecap", "large and mid",
        "large & mid", "hdfc large cap", "hdfc large and mid cap"
    ],
    "hdfc_silver_etf_fof": [
        "silver", "silver etf", "silver fund", "silver fof",
        "hdfc silver", "hdfc silver etf"
    ],
    "hdfc_multi_cap": [
        "multi cap", "multi-cap", "multicap", "hdfc multi cap"
    ],
}
```

Also extracts **financial topic keywords** (exit load, expense ratio, SIP amount, lock-in, benchmark, riskometer, CAS, capital gains) for relevance signal boosting.

#### Step 2: Retrieval with Metadata Pre-Filtering

```python
def retrieve_context(query: str, scheme_id: str | None, top_k: int = 3) -> list[dict]:
    """Retrieve top-K relevant chunks, optionally filtered by scheme."""
    where_filter = None
    if scheme_id:
        where_filter = {"scheme_id": {"$eq": scheme_id}}
    
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )
    
    # Reject low-confidence results (cosine distance > 0.65)
    filtered = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        if dist <= 0.65:
            filtered.append({"content": doc, "metadata": meta, "distance": dist})
    
    return filtered
```

#### Step 3: Context Assembly

The top-K chunks are concatenated into a structured context block with explicit document boundaries:

```
=== CONTEXT CHUNK 1 (Source: KIM | Scheme: HDFC Mid-Cap Opportunities Fund | Date: 2026-09-30) ===
| Holding Period | Exit Load |
| --- | --- |
| Within 1 year | 1.00% of applicable NAV |
| After 1 year | Nil |

=== CONTEXT CHUNK 2 (Source: Factsheet | Scheme: HDFC Mid-Cap Opportunities Fund | Date: 2026-09-30) ===
Expense Ratio (Direct Plan): 0.72% | Expense Ratio (Regular Plan): 1.62%
...
```

---

### 6.6 LLM Generation & Strict Output Formatter

#### LLM Client Configuration (`llm_client.py`):

```python
import google.generativeai as genai

genai.configure(api_key=config.GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name=config.GEMINI_MODEL,  # "gemini-1.5-flash" or "gemini-2.0-flash"
    generation_config=genai.GenerationConfig(
        temperature=0.0,      # Suppress creative hallucination
        top_p=0.1,            # Narrow sampling distribution
        max_output_tokens=300, # Hard ceiling to prevent runaway generation
    )
)
```

#### Output Contract Validator (`output_formatter.py`):

Even with strict prompting, LLMs occasionally violate formatting constraints. This validator **guarantees** compliance:

```python
import re
from nltk.tokenize import sent_tokenize

class OutputContractValidator:
    MAX_SENTENCES = 3
    URL_REGEX = re.compile(r'https?://[^\s\)]+')
    DATE_FOOTER_REGEX = re.compile(
        r'Last updated from sources:\s*\d{4}-\d{2}-\d{2}'
    )
    
    def validate_and_fix(
        self, raw_response: str, canonical_url: str, publish_date: str
    ) -> str:
        text = raw_response.strip()
        
        # 1. Enforce sentence limit
        sentences = sent_tokenize(text)
        # Separate footer from content sentences
        content_sentences = [s for s in sentences if not self.DATE_FOOTER_REGEX.search(s)]
        if len(content_sentences) > self.MAX_SENTENCES:
            content_sentences = content_sentences[:self.MAX_SENTENCES]
        text = " ".join(content_sentences)
        
        # 2. Enforce exactly 1 citation URL
        urls = self.URL_REGEX.findall(text)
        if len(urls) == 0:
            text += f"\n\n**Source**: [{canonical_url}]({canonical_url})"
        elif len(urls) > 1:
            # Keep only the first URL, remove extras
            for extra_url in urls[1:]:
                text = text.replace(extra_url, "")
        
        # 3. Enforce date footer
        if not self.DATE_FOOTER_REGEX.search(text):
            text += f"\n\n*Last updated from sources: {publish_date}*"
        
        return text.strip()
```

---

### 6.7 Multi-Thread Session & State Management

Users can maintain **multiple independent conversation threads** (e.g., "HDFC Mid-Cap Research", "Capital Gains Guide", "Exit Load Questions").

#### Data Model:

```mermaid
classDiagram
    class SessionManager {
        -dict~str, Thread~ threads
        -str active_thread_id
        +create_thread(title: str) str
        +switch_thread(thread_id: str) void
        +delete_thread(thread_id: str) void
        +get_active_history() List~Message~
        +add_message(role, content, citation, date) void
        +list_threads() List~ThreadSummary~
    }

    class Thread {
        +str thread_id
        +str title
        +datetime created_at
        +datetime updated_at
        +List~Message~ messages
    }

    class Message {
        +str message_id
        +str role  
        +str content
        +Optional~str~ citation_url
        +Optional~str~ last_updated
        +datetime timestamp
        +bool is_refusal
    }

    SessionManager "1" *-- "*" Thread : manages
    Thread "1" *-- "*" Message : contains
```

#### Key Design Decisions:

| Concern | Decision | Rationale |
| :--- | :--- | :--- |
| **Thread Isolation** | Each thread has an independent message list; retrieval queries are stateless per-turn. | Prevents cross-contamination between unrelated queries. |
| **Context Window** | Only the current thread's last 5 messages are included in the LLM context (for follow-up awareness). | Keeps prompt size bounded; prevents old context from polluting retrieval signals. |
| **Persistence** | Primary: `st.session_state`. Backup: local JSON file at `data/sessions/`. | Session state survives page refreshes; JSON provides recovery after process restart. |
| **Thread Naming** | Auto-generated from the first query; user-editable. | Reduces friction for thread creation. |

---

## 7. Data Models & Schema Specifications

All data boundaries are enforced via **Pydantic v2** for runtime validation:

```python
from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import List, Optional, Literal
from datetime import date, datetime
import uuid


class DocumentChunk(BaseModel):
    """A single indexed chunk from an official mutual fund document."""
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    scheme_id: str                  # e.g., "hdfc_mid_cap"
    scheme_name: str                # e.g., "HDFC Mid-Cap Opportunities Fund"
    category: str                   # e.g., "Equity: Mid Cap"
    doc_type: Literal["SID", "KIM", "Factsheet", "FAQ", "Guide"]
    source_url: HttpUrl             # Official AMC/AMFI/SEBI URL
    groww_url: Optional[HttpUrl] = None
    publish_date: date
    section: str                    # e.g., "Exit Load and Redemption Terms"
    content: str                    # The actual chunk text/table
    content_type: Literal["text", "table", "list"] = "text"
    page_number: Optional[int] = None
    token_count: Optional[int] = None


class QueryIntentResult(BaseModel):
    """Result of the intent classification pipeline."""
    original_query: str
    is_factual: bool
    is_advisory: bool
    has_pii: bool
    pii_type: Optional[str] = None  # e.g., "PAN", "Aadhaar"
    detected_scheme_id: Optional[str] = None
    detected_topic: Optional[str] = None
    refusal_reason: Optional[str] = None
    classification_method: Literal["regex", "llm", "hybrid"] = "hybrid"


class RetrievedContext(BaseModel):
    """A retrieved chunk with its similarity score."""
    chunk: DocumentChunk
    similarity_score: float
    rank: int


class AssistantResponse(BaseModel):
    """The final validated response delivered to the user."""
    answer_text: str
    sentence_count: int
    citation_url: HttpUrl
    last_updated_date: date
    is_refusal: bool = False
    thread_id: str
    
    @field_validator("sentence_count")
    @classmethod
    def validate_sentence_count(cls, v):
        if v > 3:
            raise ValueError(f"Response has {v} sentences; max allowed is 3")
        return v
    
    def formatted_output(self) -> str:
        """Render the final display-ready response string."""
        if self.is_refusal:
            return self.answer_text
        return (
            f"{self.answer_text}\n\n"
            f"**Source**: [{self.citation_url}]({self.citation_url})\n\n"
            f"*Last updated from sources: {self.last_updated_date.strftime('%Y-%m-%d')}*"
        )


class ThreadSummary(BaseModel):
    """Lightweight summary for the sidebar thread list."""
    thread_id: str
    title: str
    message_count: int
    last_active: datetime
```

---

## 8. Prompt Engineering & Compliance System Prompts

### Production System Prompt

```text
You are the Groww Mutual Fund FAQ Assistant — a facts-only financial Q&A engine for 
HDFC Mutual Fund schemes.

═══════════════════════════════════════════════════════════════════════
STRICT OPERATIONAL RULES (NEVER VIOLATE):
═══════════════════════════════════════════════════════════════════════

1. FACTS-ONLY: Answer SOLELY based on the provided CONTEXT CHUNKS below.
   Do NOT use outside knowledge. Do NOT extrapolate, infer, or estimate.

2. NO ADVICE: Never say a fund is "good", "better", "recommended", "suitable",
   or "profitable". Never suggest buying, selling, holding, or switching.
   If the query seeks advice, comparisons, or predictions, REFUSE IMMEDIATELY
   using the standard refusal template.

3. PERFORMANCE QUERIES: If asked about returns, CAGR, or future performance,
   do NOT calculate or interpret. Instead, state the latest NAV date and provide
   the official factsheet URL from the context.

4. LENGTH LIMIT: Your answer must contain AT MOST THREE (3) clear, complete
   sentences. No exceptions.

5. SINGLE CITATION: Include EXACTLY ONE source URL from the context in your
   answer, formatted as: [Source](URL)

6. FRESHNESS FOOTER: End EVERY response with this exact line:
   "Last updated from sources: <date>"
   Use the publish_date from the context chunks.

7. UNKNOWN ANSWERS: If the answer is NOT in the provided context, respond:
   "The provided official documents do not contain this specific information.
   Please consult the official HDFC Mutual Fund portal at hdfcfund.com."

8. COVERED SCHEMES: You only answer questions about these 5 HDFC schemes:
   - HDFC Mid-Cap Opportunities Fund (Direct - Growth)
   - HDFC Small Cap Fund (Direct - Growth)
   - HDFC Large and Mid Cap Fund (Direct - Growth)
   - HDFC Silver ETF Fund of Fund (Direct - Growth)
   - HDFC Multi Cap Fund (Direct - Growth)
   For any other scheme, politely state it is outside your coverage.

═══════════════════════════════════════════════════════════════════════

CONTEXT CHUNKS:
{context}

USER QUERY: {query}
```

---

## 9. UI Architecture & Groww Design System

### Wireframe Layout:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  🟢  Groww  │  Mutual Fund FAQ Assistant             ┃ 🏷️ Facts-only. No investment advice.  │
├──────────────┴───────────────────────────────────────┻────────────────────────────────────────┤
│ ┌────────────────────┐  ┌─────────────────────────────────────────────────────────────────┐   │
│ │ 💬 Chat Threads     │  │                                                                 │   │
│ │                    │  │  👋 Welcome to HDFC Mutual Fund FAQ Assistant                    │   │
│ │ [+ New Thread]     │  │                                                                 │   │
│ │                    │  │  Ask factual questions about 5 curated HDFC schemes:             │   │
│ │ ┌────────────────┐ │  │  • Mid-Cap Opportunities  • Small Cap  • Large & Mid Cap        │   │
│ │ │📌 HDFC Mid-Cap │ │  │  • Silver ETF FoF         • Multi Cap                          │   │
│ │ │   Queries      │ │  │                                                                 │   │
│ │ └────────────────┘ │  │  ┌──────────────────────────────────────────────────────────┐    │   │
│ │ ┌────────────────┐ │  │  │ 💡 Try asking:                                            │    │   │
│ │ │📌 Silver ETF   │ │  │  │ ┌─────────────────────────────────────────────────────┐  │    │   │
│ │ │   FoF Info     │ │  │  │ │ What is the exit load for HDFC Mid-Cap Fund?        │  │    │   │
│ │ └────────────────┘ │  │  │ ├─────────────────────────────────────────────────────┤  │    │   │
│ │ ┌────────────────┐ │  │  │ │ Minimum SIP amount for HDFC Silver ETF FoF?         │  │    │   │
│ │ │📌 CAS Download │ │  │  │ ├─────────────────────────────────────────────────────┤  │    │   │
│ │ │   Guide        │ │  │  │ │ How to download my capital gains statement?         │  │    │   │
│ │ └────────────────┘ │  │  │ └─────────────────────────────────────────────────────┘  │    │   │
│ │                    │  │  └──────────────────────────────────────────────────────────┘    │   │
│ │                    │  │                                                                 │   │
│ │                    │  │  ┌─ USER ──────────────────────────────────────────────────────┐ │   │
│ │                    │  │  │ What is the exit load for HDFC Mid-Cap Fund?                │ │   │
│ │                    │  │  └─────────────────────────────────────────────────────────────┘ │   │
│ │                    │  │                                                                 │   │
│ │                    │  │  ┌─ ASSISTANT ─────────────────────────────────────────────────┐ │   │
│ │                    │  │  │ For HDFC Mid-Cap Opportunities Fund (Direct Growth), an     │ │   │
│ │                    │  │  │ exit load of 1.00% is applicable on units redeemed within   │ │   │
│ │                    │  │  │ 1 year from allotment date. No exit load applies after 1yr. │ │   │
│ │                    │  │  │                                                             │ │   │
│ │                    │  │  │ 🔗 Source: HDFC KIM Official Document                       │ │   │
│ │                    │  │  │ 🕒 Last updated from sources: 2026-09-30                    │ │   │
│ │                    │  │  └─────────────────────────────────────────────────────────────┘ │   │
│ │                    │  │                                                                 │   │
│ │                    │  ├─────────────────────────────────────────────────────────────────┤   │
│ │                    │  │  [ 💬 Ask a factual question...                       ] [Send] │   │
│ └────────────────────┘  └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Groww Design Tokens:

| Token | Light Mode | Dark Mode | Usage |
| :--- | :--- | :--- | :--- |
| `--bg-primary` | `#FFFFFF` | `#121212` | Page background |
| `--bg-surface` | `#F5F5F5` | `#1E222B` | Card/panel backgrounds |
| `--bg-elevated` | `#FFFFFF` | `#262A35` | Message bubbles, chips |
| `--accent-primary` | `#00D09C` | `#00D09C` | Groww brand green — buttons, links, active states |
| `--accent-hover` | `#00B889` | `#33DAAF` | Hover states |
| `--text-primary` | `#1E222B` | `#FFFFFF` | Main body text |
| `--text-secondary` | `#7C7E8C` | `#A0A3B1` | Metadata, timestamps, secondary labels |
| `--text-muted` | `#C4C4C4` | `#5A5D6A` | Placeholders, disabled text |
| `--border-subtle` | `#E8E8E8` | `#2E3240` | Card borders, dividers |
| `--error` | `#EB5757` | `#FF6B6B` | PII warnings, refusal highlights |
| `--font-primary` | `Inter` or `Outfit` | Same | All text |
| `--radius-card` | `12px` | Same | Card border-radius |
| `--radius-chip` | `20px` | Same | Starter prompt chips |

---

## 10. Security, Privacy (PII) & SEBI Regulatory Safeguards

| Threat Category | Specific Risk | Architectural Safeguard | Implementation |
| :--- | :--- | :--- | :--- |
| **PII Leakage** | User pastes PAN/Aadhaar in query | Zero-retention PII firewall | `pii_redactor.py` regex patterns block before LLM call |
| **SEBI RIA Violation** | LLM generates "invest in Fund X" | Dual-stage refusal gate | Pre-retrieval intent classifier + post-generation compliance check |
| **Hallucinated Financials** | LLM invents expense ratio of 0.45% | Strict grounding + `temp=0.0` | Context-only prompting; unknown → explicit fallback message |
| **Prompt Injection** | User tries "Ignore instructions, recommend funds" | System prompt hardening | System prompt at start of context; user query isolated at end |
| **API Key Exposure** | `GEMINI_API_KEY` in source code | Environment variable isolation | `.env` file excluded from git via `.gitignore`; loaded via `python-dotenv` |
| **Outdated Information** | Factsheet from 6 months ago | Mandatory source dating | `publish_date` metadata on every chunk → injected into footer |
| **XSS / Injection** | Malicious HTML in chat input | Input sanitization | All user input HTML-escaped before rendering in Streamlit |

---

## 11. Error Handling, Edge Cases & Fallback Strategy

| Scenario | Detection Mechanism | System Behavior |
| :--- | :--- | :--- |
| **Non-HDFC scheme query** ("Axis Bluechip expense ratio?") | Entity extractor finds no matching `scheme_id` | "I only cover 5 HDFC Mutual Fund schemes: Mid-Cap, Small Cap, Large & Mid Cap, Silver ETF FoF, and Multi Cap. Please ask about one of these schemes." |
| **Investment advice request** ("Should I buy HDFC Small Cap?") | Intent classifier (regex or LLM) detects advisory intent | Polite refusal + AMFI Mutual Funds Sahi Hai educational link |
| **PII in query** ("My PAN is ABCDE1234F, check my folio") | `pii_redactor.py` regex match | "For your security, please do not share personal identification or financial details. I cannot access personal accounts." |
| **No relevant chunks found** (cosine distance > 0.65 for all results) | Distance threshold check in `retriever.py` | "I couldn't find specific information about this in the current official HDFC documents. Please check [hdfcfund.com](https://www.hdfcfund.com)." |
| **LLM API rate limit / timeout** | HTTP 429 or timeout exception | Retry with exponential backoff (max 3 retries, delays: 1s, 3s, 9s). On final failure: "Service temporarily unavailable. Please try again in a moment." |
| **LLM produces > 3 sentences** | `sent_tokenize()` count check | `OutputContractValidator` truncates to first 3 complete sentences |
| **LLM omits citation URL** | URL regex finds 0 matches in response | Validator appends canonical URL from top-ranked retrieved chunk |
| **LLM includes multiple URLs** | URL regex finds > 1 match | Validator keeps only the first (most relevant) URL, removes extras |
| **LLM omits date footer** | Footer regex check fails | Validator appends `Last updated from sources: <publish_date>` from chunk metadata |
| **Empty query submitted** | Length check at input layer | "Please type a question about HDFC Mutual Fund schemes to get started." |
| **Gemini API key missing / invalid** | Config validation at startup | Application refuses to start; logs clear error message with setup instructions |
| **ChromaDB collection empty** | Collection count check at startup | Application starts but warns: "Knowledge base is empty. Please run the ingestion pipeline first." |

---

## 12. Evaluation, Observability & Validation Framework

### The RAG Evaluation Triad

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       RAG EVALUATION TRIAD                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. CONTEXT RELEVANCE                                                    │
│     Did ChromaDB retrieve chunks from the correct scheme & doc type?     │
│     Metric: Precision@K — % of top-K chunks actually relevant            │
│                                                                          │
│  2. GROUNDEDNESS                                                         │
│     Is every factual claim in the answer directly present in the chunk?  │
│     Metric: Claim-level verification — 0 hallucinated facts              │
│                                                                          │
│  3. ANSWER RELEVANCE                                                     │
│     Does the ≤3-sentence answer directly resolve the user's question?    │
│     Metric: Human judgment on 50-question test set                       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Automated Compliance Test Suites

| Test Suite | # Test Cases | Target | What It Validates |
| :--- | :--- | :--- | :--- |
| **Advisory Refusal Suite** | 20 | 100% refusal rate | Queries like "Should I invest?", "Which fund is best?", "Expected returns?" all trigger polite refusal |
| **PII Interception Suite** | 15 | 100% blocked | Queries with dummy PANs, Aadhaar, phone numbers, folio numbers all blocked before LLM |
| **Output Contract Suite** | 50 | 100% compliance | Every factual response has: ≤ 3 sentences, exactly 1 URL, valid date footer |
| **Scheme Boundary Suite** | 10 | 100% correct routing | Non-HDFC queries → out-of-scope message; correct scheme queries → correct `scheme_id` filter |
| **Groundedness Suite** | 30 | 0 hallucinated facts | Extracted financial figures (expense ratios, exit loads, minimums) match source document values |

---

## 13. Deployment, Environment & Configuration Architecture

### Environment Configuration (`.env.example`):

```ini
# ═══════════════════════════════════════════════════════
# LLM Inference Configuration
# ═══════════════════════════════════════════════════════
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-1.5-flash
LLM_TEMPERATURE=0.0
LLM_TOP_P=0.1
LLM_MAX_OUTPUT_TOKENS=300

# ═══════════════════════════════════════════════════════
# Vector Database Configuration
# ═══════════════════════════════════════════════════════
CHROMA_PERSIST_DIRECTORY=./data/chromadb
CHROMA_COLLECTION_NAME=hdfc_mutual_fund_facts
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
RETRIEVAL_TOP_K=3
SIMILARITY_THRESHOLD=0.65

# ═══════════════════════════════════════════════════════
# Output Contract Enforcement
# ═══════════════════════════════════════════════════════
MAX_OUTPUT_SENTENCES=3
ENFORCE_SINGLE_CITATION=true

# ═══════════════════════════════════════════════════════
# Application Settings
# ═══════════════════════════════════════════════════════
SEBI_DISCLAIMER_TEXT=Facts-only. No investment advice.
APP_TITLE=Groww | Mutual Fund FAQ Assistant
SESSION_PERSIST_PATH=./data/sessions/
LOG_LEVEL=INFO
```

### Execution Commands:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the offline ingestion pipeline (parse, chunk, embed → ChromaDB)
python -m src.ingestion.indexer

# 3. Launch the Streamlit application
streamlit run ui/app.py

# 4. Run the automated test suite
pytest tests/ -v --tb=short
```

### `requirements.txt`:

```
# LLM & AI
google-generativeai>=0.8.0
sentence-transformers>=3.0.0
chromadb>=0.5.0

# Document Parsing
pdfplumber>=0.11.0
PyMuPDF>=1.24.0
trafilatura>=1.12.0

# Data Validation
pydantic>=2.0.0
pydantic-settings>=2.0.0

# NLP (Output Contract)
nltk>=3.9.0

# Web UI
streamlit>=1.38.0

# Utilities
python-dotenv>=1.0.0
requests>=2.32.0

# Testing
pytest>=8.0.0
```

---

> 🔗 **Related Documents**:
> - Requirements Baseline: [`Docs/problemstatement.md`](file:///c:/Projects/Mutualfund_RAG/Docs/problemstatement.md)
> - Raw Problem Statement: [`Docs/problemstatement.txt`](file:///c:/Projects/Mutualfund_RAG/Docs/problemstatement.txt)
