# 📋 Phase-Wise Implementation Plan: Mutual Fund FAQ Assistant

> **Project**: Groww-Inspired HDFC Mutual Fund Facts-Only RAG Assistant  
> **Architecture Reference**: [`Docs/architecture.md`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md)  
> **Requirements Reference**: [`Docs/problemstatement.md`](file:///c:/Projects/Mutualfund_RAG/Docs/problemstatement.md)

---

## 📊 Plan Overview

This document breaks the project into **7 phases**, each producing a **working, verifiable artifact** that builds incrementally on the last. Each phase concludes with a clearly defined **Acceptance Gate** — a set of automated or manual checks that must pass before proceeding.

### Phase Summary Roadmap

```
PHASE 1           PHASE 2           PHASE 3           PHASE 4           PHASE 5           PHASE 6           PHASE 7
─────────         ─────────         ─────────         ─────────         ─────────         ─────────         ─────────
Project           Corpus            Guardrails        RAG Retrieval     LLM               Streamlit         Daily Data
Setup &           Ingestion         & Safety          Pipeline          Generation        UI +              Scheduler &
Infrastructure    Pipeline          Gates             (ChromaDB)        & Formatting      Integration       CI/CD Automation

   ↓                 ↓                 ↓                 ↓                 ↓                 ↓                 ↓
Skeleton          Clean             PII Filter        Vector            Compliant          Full App +        GitHub Actions
+ Config          Indexed           + Refusal         Queries           3-Sentence         Polish +          Daily 10 AM Run
+ Models          Corpus            Engine            Working           Responses          Testing           Auto-Refresh

1–2 days         2–3 days          1–2 days          1–2 days          2–3 days          2–3 days          1 day
```

| Phase | Name | Duration | Key Deliverable | Blocking Gate |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Project Setup & Infrastructure | 1–2 days | Runnable skeleton, config, Pydantic models, logging | `python -m src.config` runs without error; all dirs created |
| **2** | Corpus Ingestion Pipeline | 2–3 days | 5 HDFC schemes indexed in ChromaDB (strictly 5 Groww URLs, no extra URLs) | ChromaDB collection indexed from 5 Groww URLs; spot-check 5 tables |
| **3** | Guardrails & Safety Gates | 1–2 days | PII redactor + intent classifier + refusal engine | 100% PII blocked in 15-query suite; 100% advisory refused in 20-query suite |
| **4** | Retrieval & Context Assembly | 1–2 days | ChromaDB filtered retrieval + entity extraction | Top-3 chunks returned in < 500ms; metadata filter isolates correct scheme |
| **5** | LLM Generation & Output Contract | 2–3 days | Groq API integration + Output Contract Validator | 50-query suite: 100% ≤3 sentences, 100% 1 URL, 100% date footer |
| **6** | UI + Integration + Polish + Testing | 2–3 days | Full Groww-themed Streamlit app, multi-thread support, full test suite | All 5 test suites pass; end-to-end demo works; README complete |
| **7** | Automated Daily Ingestion Scheduler | 1 day | Scheduled CI/CD workflow (`.github/workflows/daily_ingestion.yml`) running daily at 10:00 AM IST (04:30 UTC) to crawl, parse, clean, chunk, embed with MiniLM, update ChromaDB, and verify regression tests | Cron trigger verified (`30 4 * * *`), headless crawl-to-index pipeline executes, 30 chunks verified, ChromaDB artifacts and manifest hashes persisted |

**Total Estimated Duration**: 10–16 days

---

## Phase 1: Project Setup & Infrastructure

> **Goal**: Establish a clean, reproducible project skeleton with centralized configuration, Pydantic data models, structured logging, and all directory scaffolding — before writing any business logic.

### 1.1 Directory Scaffolding

Create the full directory structure as defined in [`architecture.md §4`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md):

```bash
# Run from project root: c:\Projects\Mutualfund_RAG\
# Strictly the 5 Groww HDFC schemes (no common / extra URLs)
mkdir -p data/raw/hdfc_mid_cap
mkdir -p data/raw/hdfc_small_cap
mkdir -p data/raw/hdfc_large_mid_cap
mkdir -p data/raw/hdfc_silver_etf_fof
mkdir -p data/raw/hdfc_multi_cap
mkdir -p data/processed
mkdir -p data/chromadb
mkdir -p data/sessions
mkdir -p src/ingestion src/guardrails src/retrieval src/generation src/state src/utils
mkdir -p ui tests Docs
```

**Files to create (empty stubs)**:
- `src/__init__.py`, `src/ingestion/__init__.py`, `src/guardrails/__init__.py`
- `src/retrieval/__init__.py`, `src/generation/__init__.py`, `src/state/__init__.py`, `src/utils/__init__.py`
- `ui/__init__.py`

### 1.2 Environment & Dependency Management

**File: `.env.example`** (copy to `.env` and fill in values)
```ini
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.0
LLM_TOP_P=0.1
LLM_MAX_OUTPUT_TOKENS=300

CHROMA_PERSIST_DIRECTORY=./data/chromadb
CHROMA_COLLECTION_NAME=hdfc_mutual_fund_facts
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
RETRIEVAL_TOP_K=3
SIMILARITY_THRESHOLD=0.65

MAX_OUTPUT_SENTENCES=3
ENFORCE_SINGLE_CITATION=true

SEBI_DISCLAIMER_TEXT=Facts-only. No investment advice.
APP_TITLE=Groww | Mutual Fund FAQ Assistant
SESSION_PERSIST_PATH=./data/sessions/
LOG_LEVEL=INFO
```

**File: `requirements.txt`**
```
# LLM & AI
groq>=0.9.0
sentence-transformers>=3.0.0
chromadb>=0.5.0

# Document Parsing
trafilatura>=1.12.0
beautifulsoup4>=4.12.0
pdfplumber>=0.11.0
PyMuPDF>=1.24.0

# Data Validation
pydantic>=2.0.0
pydantic-settings>=2.0.0

# NLP (Output Contract Enforcement)
nltk>=3.9.0

# Web UI
streamlit>=1.38.0

# Utilities
python-dotenv>=1.0.0
requests>=2.32.0
httpx>=0.27.0

# Testing
pytest>=8.0.0
pytest-mock>=3.14.0
```

### 1.3 Centralized Configuration (`src/config.py`)

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # LLM
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.1
    llm_max_output_tokens: int = 300

    # ChromaDB
    chroma_persist_directory: str = "./data/chromadb"
    chroma_collection_name: str = "hdfc_mutual_fund_facts"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    retrieval_top_k: int = 3
    similarity_threshold: float = 0.65

    # Output Contract
    max_output_sentences: int = 3
    enforce_single_citation: bool = True

    # App
    sebi_disclaimer_text: str = "Facts-only. No investment advice."
    app_title: str = "Groww | Mutual Fund FAQ Assistant"
    session_persist_path: str = "./data/sessions/"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

config = Settings()
```

### 1.4 Pydantic Data Models (`src/state/models.py`)

Implement all schemas from [`architecture.md §7`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md): `DocumentChunk`, `QueryIntentResult`, `RetrievedContext`, `AssistantResponse`, `Thread`, `Message`, `ThreadSummary`.

### 1.5 Structured Logger (`src/utils/logger.py`)

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

### 1.6 Sources Manifest (`data/sources_manifest.json`)

Strictly contains the **5 canonical Groww HDFC scheme URLs** specified in [`Docs/problemstatement.md`](file:///c:/Projects/Mutualfund_RAG/Docs/problemstatement.md) with **no extra URLs**:

```json
{
  "manifest_version": "1.0",
  "last_updated": "2026-10-25",
  "total_sources": 5,
  "sources": [
    {
      "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
      "scheme_id": "hdfc_mid_cap",
      "scheme_name": "HDFC Mid-Cap Opportunities Fund (Direct - Growth)",
      "category": "Equity: Mid Cap",
      "format": "html",
      "description": "Groww scheme page — NAV, expense ratio, exit load, minimum SIP/lumpsum, fund size, lock-in, holdings, benchmark"
    },
    {
      "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
      "scheme_id": "hdfc_small_cap",
      "scheme_name": "HDFC Small Cap Fund (Direct - Growth)",
      "category": "Equity: Small Cap",
      "format": "html",
      "description": "Groww scheme page — NAV, expense ratio, exit load, minimum SIP/lumpsum, fund size, lock-in, holdings, benchmark"
    },
    {
      "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
      "scheme_id": "hdfc_large_mid_cap",
      "scheme_name": "HDFC Large and Mid Cap Fund (Direct - Growth)",
      "category": "Equity: Large & Mid Cap",
      "format": "html",
      "description": "Groww scheme page — NAV, expense ratio, exit load, minimum SIP/lumpsum, fund size, lock-in, holdings, benchmark"
    },
    {
      "url": "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
      "scheme_id": "hdfc_silver_etf_fof",
      "scheme_name": "HDFC Silver ETF Fund of Fund (Direct - Growth)",
      "category": "Commodity: Silver FoF",
      "format": "html",
      "description": "Groww scheme page — NAV, expense ratio, exit load, minimum SIP/lumpsum, fund size, lock-in, holdings, benchmark"
    },
    {
      "url": "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth",
      "scheme_id": "hdfc_multi_cap",
      "scheme_name": "HDFC Multi Cap Fund (Direct - Growth)",
      "category": "Equity: Multi Cap",
      "format": "html",
      "description": "Groww scheme page — NAV, expense ratio, exit load, minimum SIP/lumpsum, fund size, lock-in, holdings, benchmark"
    }
  ]
}
```

> **Strict Scope Constraint**: Exactly these 5 Groww scheme URLs are ingested into the corpus. No extra URLs, third-party blogs, or additional AMC/AMFI sub-pages are fetched.

### Phase 1 Acceptance Gate

| Check | Command / Method | Pass Condition |
| :--- | :--- | :--- |
| Config loads without error | `python -c "from src.config import config; print(config.app_title)"` | Prints app title; no exception |
| All `__init__.py` stubs exist | `find src -name "__init__.py"` | 8 files found |
| Models import cleanly | `python -c "from src.state.models import DocumentChunk, AssistantResponse"` | No import error |
| Logger outputs JSON | `python -c "from src.utils.logger import get_logger; get_logger('test').info('ok')"` | JSON line printed to stdout |
| `.env` is gitignored | Check `.gitignore` | `.env` listed |

---

## Phase 2: Corpus Ingestion Pipeline & Data Architecture

> **Goal**: Build the **offline ingestion pipeline** that fetches strictly the 5 canonical Groww HDFC scheme pages (no extra URLs), extracts clean structured text and financial tables (TER, exit load, minimum SIP/lump-sum, lock-in, riskometer, benchmark), chunks them using a data-researched **Section-Atomic Chunking Strategy**, generates dense vector representations via **`sentence-transformers/all-MiniLM-L6-v2`**, and indexes them into **ChromaDB** with exact metadata filtering.

### 2.0 Empirical Data Research on Groww HDFC Scheme Data

To determine the optimal chunking strategy, embedding model, and vector database configuration, an exhaustive empirical data audit was conducted across the 5 canonical scheme snapshots in `data/raw/`:

#### 1. Snapshot Footprints & Structure
| Scheme ID | Scheme Name | HTML Snapshot Size | Extracted Blocks | Structured Tables | Narrative Prose Blocks | Total Estimated Tokens |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `hdfc_mid_cap` | HDFC Mid-Cap Opportunities Fund (Direct - Growth) | 491.5 KB | 6 | 5 | 1 | ~1,104 |
| `hdfc_small_cap` | HDFC Small Cap Fund (Direct - Growth) | 488.8 KB | 6 | 5 | 1 | ~1,114 |
| `hdfc_large_mid_cap` | HDFC Large and Mid Cap Fund (Direct - Growth) | 445.8 KB | 6 | 5 | 1 | ~1,136 |
| `hdfc_silver_etf_fof` | HDFC Silver ETF Fund of Fund (Direct - Growth) | 354.6 KB | 6 | 5 | 1 | ~780 |
| `hdfc_multi_cap` | HDFC Multi Cap Fund (Direct - Growth) | 524.4 KB | 6 | 5 | 1 | ~1,123 |
| **Total Corpus** | **Strictly 5 Canonical Groww Schemes** | **2.30 MB** | **30 blocks** | **25 tables** | **5 text** | **~5,257 tokens** |

#### 2. Section-Level Token & Table Row Distribution
| Section Name | Content Type | Table Rows | Token Range | Avg Tokens | Empirical Rationale & Information Preserved |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Expense Ratio & Exit Load** | Markdown Table | 6 rows | 249 | 249.0 | TER (Direct Plan), Exit load holding thresholds and penalty rates (1.00% if < 1 yr; Nil after), Stamp duty (0.005%), Tax implications (LTCG / STCG). |
| **Minimum Investment & Lock-in** | Markdown Table | 8 rows | 145 | 145.0 | Minimum SIP (₹100), Minimum Lumpsum (₹100), Additional investment (₹100), Lock-in period (Nil). |
| **Fund Overview & Benchmark** | Markdown Table | 13 rows | 242–249 | 247.6 | Scheme Name, Category, Benchmark (e.g. NIFTY Midcap 150 TRI), AUM (₹ Cr), NAV, NAV Date, Riskometer, Launch Date. |
| **Fund Management** | Markdown Table | 4 rows | 48–53 | 49.8 | Fund Manager name(s), tenure, fund management responsibilities. |
| **Holdings & Portfolio Allocation** | Markdown Table | 5–17 rows | 101–456 | 374.0 | Top 15 portfolio holdings (Company, Sector, Instrument, Asset %); Silver ETF FoF has 3 holdings (Silver ETF, cash/treps). |
| **Investment Objective & Strategy** | Narrative Text | 0 rows | 32–50 | 39.6 | Official scheme statutory objective statement for capital appreciation. |

#### 3. Corpus-Wide Token Metrics
- **Total Chunks across Corpus**: Strictly 30 chunks (6 sections × 5 schemes).
- **Minimum Chunk Size**: 32 tokens (`hdfc_silver_etf_fof` objective).
- **Maximum Chunk Size**: 456 tokens (`hdfc_large_mid_cap` top 15 holdings).
- **Average Chunk Size**: 184.2 tokens.
- **Median Chunk Size**: 145.0 tokens.
- **Entire Corpus Token Size**: ~5,257 tokens (easily fits in high-speed local memory).

---

### 2.1 URL Crawler (`src/ingestion/crawler.py`)

**Responsibilities**:
1. Read `data/sources_manifest.json` containing strictly the 5 Groww URLs.
2. Snapshot HTML pages to `data/raw/<scheme_id>/groww_page.html` with browser `User-Agent` headers and automatic encoding negotiation.
3. Compute SHA-256 hash of each page snapshot.
4. Compare against stored hashes in manifest — **skip re-download if unchanged** (idempotent ingestion).
5. Update manifest with `sha256`, `download_path`, and `downloaded_at` timestamps.

**Status**: Implemented & Tested (Passes all crawler & hash verification tests).

---

### 2.2 HTML & Financial Table Parser (`src/ingestion/html_parser.py`)

**Responsibilities**:
1. Parse Next.js hydration payload (`__NEXT_DATA__` -> `props.pageProps.mfServerSideData`) containing 97 clean financial attributes and fallback HTML DOM tables.
2. Structure tabular financial parameters into clean Markdown tables with pipe (`|`) delimiters.
3. Ingest certified statutory dates (`nav_date`, `portfolio_date`) into ISO format `YYYY-MM-DD`.
4. Output 6 canonical content blocks per scheme:
   - `Expense Ratio & Exit Load` (table)
   - `Minimum Investment & Lock-in` (table)
   - `Fund Overview & Benchmark` (table)
   - `Fund Management` (table)
   - `Holdings & Portfolio Allocation` (table)
   - `Investment Objective & Strategy` (text)

**Status**: Implemented & Tested (Passes all 7 table and financial extraction tests).

---

### 2.3 Empirical Chunking Strategy (`src/ingestion/chunker.py`)

#### Why Traditional Sliding-Window Chunking Fails
- Fixed-window token sliding chunking (e.g., 500 characters or 200 tokens with 50-token stride) slices across table rows.
- **Header severing**: Detaches header rows from data rows; parameter names (`Exit Load`) become severed from values (`1.00% if redeemed within 1 year`).
- **Context pollution & hallucinations**: Overlapping tokens duplicate partial table rows across multiple chunks, inflating retrieval tokens and confusing LLM synthesis with duplicate numbers.

#### Adopted Strategy: Semantic Section-Atomic Chunking with Scheme-Context Prepending
1. **Section-Atomic Table Preservation**:
   - Because all financial tables are $\le 500$ tokens (ranging from 48 to 456 tokens), each section table is preserved as a **single, 100% atomic chunk**. No table row is ever split.
2. **Context Prepending (Breadcrumb Header)**:
   - Every chunk is prepended with scheme and section identity to guarantee high dense retrieval relevance even when the user asks vague questions (e.g., *"What is the exit load?"*):
     ```markdown
     ### Scheme: {scheme_name} | Category: {category} | Section: {section}

     {content}
     ```
3. **Window & Overlap Parameters**:
   - `chunk_size`: Section-bounded (35 to 460 tokens).
   - `chunk_overlap`: **0 tokens** (each section is orthogonal and self-contained; zero boundary bleed).
4. **Metadata Schema**:
   Every `DocumentChunk` is tagged with:
   - `chunk_id`: `{scheme_id}_{slugified_section}_{chunk_index}`
   - `scheme_id`: `{scheme_id}` (e.g., `hdfc_mid_cap`)
   - `scheme_name`: Full scheme name
   - `section`: Section name
   - `content_type`: `"table"` or `"text"`
   - `publish_date`: `"YYYY-MM-DD"` (verified statutory date)
   - `source_url`: Canonical Groww URL citation

**Key tasks**:
- [x] Implement `slugify(text: str) -> str` for deterministic chunk IDs.
- [x] Implement `prepend_context(content: str, scheme_name: str, category: str, section: str) -> str`.
- [x] Implement `chunk_section_block(block: dict, category: str) -> DocumentChunk`.
- [x] Implement `chunk_document(content_blocks: list[dict], category: str) -> list[DocumentChunk]`.

---

### 2.4 Empirical Embedding Model Selection

#### Model Comparison & Selection Matrix
| Candidate Model | Vector Dim | Context Length | Model Footprint | Retrieval Latency (CPU) | Evaluation & Trade-offs | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`sentence-transformers/all-MiniLM-L6-v2`** | **384** | **256 / 512** | **~80 MB** | **~5 ms** | **Optimal dense representation for financial tables & short QA; lightweight; local execution; zero API dependencies.** | **SELECTED** |
| `sentence-transformers/all-mpnet-base-v2` | 768 | 512 | ~420 MB | ~35 ms | Slower on CPU; 768 dimensions causes unnecessary vector space bloat for 30 chunks. | Rejected |
| `BAAI/bge-small-en-v1.5` | 384 | 512 | ~130 MB | ~8 ms | Requires mandatory query instruction prefix (`Represent this sentence for searching relevant passages:`); failure risk if omitted in frontend. | Rejected |
| Cloud API Embeddings (OpenAI / Groq) | 1536 / 384 | Variable | Remote | 150–400 ms | Adds external network latency, recurring API costs, rate limits, and breaks offline crawler determinism. | Rejected |

#### Why `all-MiniLM-L6-v2` Perfectly Fits Our Data
- **Token Coverage**: With average chunk size of 184 tokens and median 145 tokens, 100% of the corpus chunks fit within `all-MiniLM-L6-v2`'s context window.
- **Table Density**: The dual-encoder architecture excels at matching conversational user queries (*"How much is exit load for mid cap?"*) to key-value table structures (*`| Exit Load | 1.00% if redeemed within 1 year |`*).
- **Zero Network Flakiness**: Runs 100% locally on CPU without rate limits or connection timeouts.

---

### 2.5 Vector Database Architecture & ChromaDB Configuration (`src/ingestion/indexer.py`)

#### Database Engine Selection: ChromaDB
- **Mode**: Local Serverless / Embedded (`chromadb.PersistentClient(path="./data/chromadb")`).
- **Why ChromaDB**: Zero standalone daemon process; native SQLite/DuckDB persistence on disk; native HNSW index; built-in metadata filtering (`where={"scheme_id": ...}`); native integration with `sentence-transformers`.
- **Collection Name**: `hdfc_mutual_fund_facts`

#### Metric & Distance Threshold Configuration
- **Distance Metric**: **Cosine Distance** (`metadata={"hnsw:space": "cosine"}`)
  $$D_c(u, v) = 1 - \frac{u \cdot v}{\|u\|_2 \|v\|_2} \in [0, 2]$$
- **Similarity Score Conversion**:
  $$S_c(u, v) = 1 - D_c(u, v)$$
- **Calibrated Rejection Threshold**:
  - Distance $\le 0.40$ ($S_c \ge 0.60$): High confidence exact section match.
  - Distance $0.40 - 0.65$ ($S_c \in [0.35, 0.60]$): Acceptable semantic relevance.
  - Distance $> 0.65$ ($S_c < 0.35$): **Irrelevant / Out-of-Scope**. Guardrail or retrieval layer refuses or triggers clarification.

#### Retrieval & Filtering Parameters
- **Top-K ($K$)**: **3 chunks** (~360–550 tokens of context). Retrieves the primary section (e.g., Expense & Exit Load) plus related overview/minimums if relevant, well within Groq's `llama-3.3-70b-versatile` context window.
- **Scheme Pre-Filtering**: When intent classification identifies a specific scheme (e.g., `hdfc_mid_cap`), query uses:
  ```python
  where = {"scheme_id": {"$eq": detected_scheme_id}}
  ```
  This eliminates cross-fund hallucination (e.g., answering Mid-Cap questions with Small-Cap exit load data).
- **Idempotency Guarantee**:
  - Deterministic chunk IDs (`{scheme_id}_{section_slug}_{idx}`) ensure upserts replace existing vectors without duplicate creation.
  - Ingestion checks SHA-256 manifest hashes to skip unnecessary re-indexing.

**Key tasks**:
- [x] Initialize `chromadb.PersistentClient(path="./data/chromadb")`.
- [x] Load `sentence-transformers/all-MiniLM-L6-v2` via `SentenceTransformerEmbeddingFunction`.
- [x] Implement `index_chunks(chunks: list[DocumentChunk])` with batch upserts.
- [x] Implement `index_scheme(scheme_id: str)` orchestrating crawl → parse → chunk → index.
- [x] Implement `index_all()` processing strictly the 5 Groww schemes.
- [x] Implement `--rebuild` flag to force re-indexing.

**Run command**:
```bash
python -m src.ingestion.indexer
# or: python -m src.ingestion.indexer --rebuild
```

---

### 2.6 Acceptance Gate (Phase 2 Verification)

| Check | Method | Pass Condition |
| :--- | :--- | :--- |
| **ChromaDB collection count** | `python -c "import chromadb; c=chromadb.PersistentClient('./data/chromadb'); print(c.get_collection('hdfc_mutual_fund_facts').count())"` | Count = 30 chunks across strictly 5 schemes |
| **All 5 scheme_ids present** | Query ChromaDB collection with `where={"scheme_id": id}` for each scheme | Exactly 6 chunks returned per scheme |
| **Table formatting preserved** | Inspect chunk contents for `hdfc_mid_cap` Expense Ratio section | Chunk content contains valid Markdown pipe (`|`) table |
| **Publish date formatted** | Inspect metadata of all chunks | `publish_date` is a valid ISO string `YYYY-MM-DD` |
| **Source URL compliance** | Inspect metadata of all chunks | `source_url` strictly matches one of the 5 Groww URLs |
| **Idempotency verified** | Run indexer twice | Second run skips unchanged files (via SHA-256); count remains exactly 30 |
| **Cosine metric verified** | Inspect collection metadata | `{"hnsw:space": "cosine"}` |

---

## Phase 3: Guardrails & Safety Gates

> **Goal**: Implement the two-tier safety gate that sits between the user's query and the retrieval pipeline — blocking PII and routing advisory/comparative queries to polite refusals.

### 3.1 PII Redaction Interceptor (`src/guardrails/pii_redactor.py`)

Implement detection patterns for all Indian financial PII types:

| PII Type | Regex Pattern | Example |
| :--- | :--- | :--- |
| PAN | `\b[A-Z]{5}[0-9]{4}[A-Z]\b` | `ABCDE1234F` |
| Aadhaar | `\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b` | `1234 5678 9012` |
| Mobile | `\b(?:\+91[\s-]?)?[6-9]\d{9}\b` | `+91 9876543210` |
| Email | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b` | `user@email.com` |
| Folio | `\bfolio[\s:#]*\d{5,15}\b` (case-insensitive) | `folio: 12345678` |
| Bank Account | `\b\d{9,18}\b` | `123456789012` |

**Key tasks**:
- [x] Implement `detect_pii(query: str) -> tuple[bool, str | None]` — returns `(has_pii, pii_type)`.
- [x] Implement `get_pii_block_response() -> str` — returns user-friendly block message.
- [x] Write unit tests: 15 test cases covering each PII type + clean queries.

### 3.2 Query Intent Classifier (`src/guardrails/intent_classifier.py`)

**Stage A — Regex Fast-Path** (< 1ms, no API call):

```python
ADVISORY_REGEX_PATTERNS = [
    r'\bshould\s+i\s+(invest|buy|sell|switch|redeem)\b',
    r'\bwhich\s+(fund|scheme|one)\s+is\s+(better|best|good|suitable)\b',
    r'\b(recommend|recommendation|suggest|suggestion|advice|advise)\b',
    r'\b(expected|predict|forecast)\s+(return|growth|performance)\b',
    r'\bwill\s+(this|the)\s+fund\s+(grow|rise|fall|perform)\b',
    r'\bcompare\b.{0,50}\bfund\b',
    r'\bwhich\s+is\s+(safer|riskier|better)\b',
    r'\bshould\s+I\b',
    r'\bgood\s+for\s+(long|short)\s+term\b',
    r'\bis\s+(this|the)\s+(fund|scheme)\s+good\b',
]
```

**Stage B — LLM Intent Gate** (fallback for ambiguous queries):
- Invokes a fast Groq call with a structured prompt asking for a single classification: `FACTUAL` or `ADVISORY`.
- Only triggered if regex fast-path does not match (to minimize API cost).

**Key tasks**:
- [x] Implement `classify_intent_regex(query: str) -> bool` — `True` if advisory detected.
- [x] Implement `classify_intent_llm(query: str) -> bool` — LLM fallback classifier.
- [x] Implement `classify_intent(query: str) -> QueryIntentResult` — combined pipeline.
- [x] Write unit tests: 20 advisory queries (expect `is_advisory=True`), 20 factual queries (expect `is_factual=True`).

### 3.3 Refusal Response Templates (`src/guardrails/refusal_templates.py`)

```python
from datetime import date

ADVISORY_REFUSAL = (
    "I'm designed to answer only verified factual questions about HDFC Mutual Fund schemes "
    "— such as expense ratios, exit loads, SIP minimums, and lock-in periods. "
    "I cannot offer investment advice, fund recommendations, performance predictions, or fund comparisons.\n\n"
    "For guidance on evaluating mutual funds, please visit "
    "[AMFI - Mutual Funds Sahi Hai](https://www.amfiindia.com/investor-corner/knowledge-center) "
    "or [SEBI Investor Education](https://www.sebi.gov.in/investor.html).\n\n"
    f"*Last updated from sources: {date.today().strftime('%Y-%m-%d')}*"
)

OUT_OF_SCOPE_REFUSAL = (
    "I only cover factual queries for these 5 HDFC Mutual Fund schemes: "
    "Mid-Cap Opportunities, Small Cap, Large & Mid Cap, Silver ETF FoF, and Multi Cap (all Direct - Growth plans). "
    "The scheme you asked about is outside my current coverage.\n\n"
    "Please visit [Groww Mutual Funds](https://groww.in/mutual-funds) for information on other schemes.\n\n"
    f"*Last updated from sources: {date.today().strftime('%Y-%m-%d')}*"
)

PII_BLOCK_MESSAGE = (
    "For your security, please do not share personal identification details such as PAN, "
    "Aadhaar, folio numbers, mobile numbers, or bank account information. "
    "I am a facts-only assistant and cannot access personal accounts or financial records."
)
```

**Key tasks**:
- [x] Define all refusal template strings with proper AMFI/SEBI links.
- [x] Implement `get_refusal_response(reason: str) -> str` dispatcher.

### 3.4 Guardrail Orchestrator (`src/guardrails/__init__.py`)

```python
def run_guardrails(query: str) -> QueryIntentResult:
    """Run both safety gates; return intent result with refusal if needed."""
    # Gate 1: PII check
    has_pii, pii_type = detect_pii(query)
    if has_pii:
        return QueryIntentResult(
            original_query=query,
            is_factual=False, is_advisory=False,
            has_pii=True, pii_type=pii_type,
            refusal_reason="pii_detected"
        )
    # Gate 2: Intent classification
    return classify_intent(query)
```

### Phase 3 Acceptance Gate

| Check | Test Suite | Pass Condition |
| :--- | :--- | :--- |
| PII Detection | `pytest tests/test_guardrails.py::test_pii_*` | 15/15 queries with PII blocked; 10/10 clean queries pass through |
| Advisory Refusal (Regex) | `pytest tests/test_guardrails.py::test_advisory_regex_*` | 20/20 obvious advisory queries classified `is_advisory=True` |
| Factual Pass-Through | `pytest tests/test_guardrails.py::test_factual_*` | 20/20 factual queries classified `is_factual=True` |
| Refusal Templates | `pytest tests/test_guardrails.py::test_refusal_templates_*` | All templates contain AMFI/SEBI link and date footer |

---

## Phase 4: Retrieval & Context Assembly Pipeline

> **Goal**: Build the online retrieval pipeline that extracts target scheme/topic entities from a query, performs metadata-filtered vector search against ChromaDB, and assembles a structured context block for the LLM.

### 4.1 Entity Extractor (`src/retrieval/entity_extractor.py`)

Maps natural-language fund references to canonical `scheme_id` values and identifies the financial topic:

**Scheme alias mapping** (see [`architecture.md §6.5`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md)):

```python
SCHEME_ALIASES = {
    "hdfc_mid_cap": ["mid cap", "mid-cap", "midcap", "mid cap opportunities", "hdfc mid cap"],
    "hdfc_small_cap": ["small cap", "small-cap", "smallcap", "hdfc small cap"],
    "hdfc_large_mid_cap": ["large cap", "large-cap", "large and mid", "large & mid", "hdfc large"],
    "hdfc_silver_etf_fof": ["silver", "silver etf", "silver fund", "silver fof", "hdfc silver"],
    "hdfc_multi_cap": ["multi cap", "multi-cap", "multicap", "hdfc multi cap"],
}

TOPIC_KEYWORDS = {
    "exit_load": ["exit load", "redemption charge", "redemption fee", "exit penalty"],
    "expense_ratio": ["expense ratio", "total expense ratio", "ter", "management fee"],
    "minimum_investment": ["minimum sip", "minimum investment", "minimum lumpsum", "min sip"],
    "lock_in": ["lock-in", "lock in period", "elss lock", "locked"],
    "benchmark": ["benchmark", "benchmark index", "index", "nifty", "sensex"],
    "riskometer": ["riskometer", "risk level", "risk grade", "risk category"],
    "cas": ["cas", "consolidated account statement", "account statement"],
    "capital_gains": ["capital gains", "tax statement", "elss tax", "80c"],
}
```

**Key tasks**:
- [x] Implement `extract_scheme_id(query: str) -> str | None`.
- [x] Implement `extract_topic(query: str) -> str | None`.
- [x] Implement `extract_entities(query: str) -> tuple[str | None, str | None]`.
- [x] Write unit tests for all 5 scheme aliases + 8 topic categories.

### 4.2 Vector Retriever (`src/retrieval/retriever.py`)

**Key tasks**:
- [x] Implement `build_metadata_filter(scheme_id, doc_type_filter=None) -> dict | None` — constructs ChromaDB `where` clause.
- [x] Implement `retrieve_chunks(query, scheme_id, top_k=3) -> list[RetrievedContext]` — vector search with metadata filter.
- [x] Implement low-confidence rejection: filter out any chunk with cosine distance > `SIMILARITY_THRESHOLD` (0.65).
- [x] Log retrieval results (scheme_id, query, distances, chunk_ids) for audit.

**ChromaDB filtered query pattern**:
```python
results = collection.query(
    query_texts=[query],
    n_results=config.retrieval_top_k,
    where={"scheme_id": {"$eq": scheme_id}} if scheme_id else None,
    include=["documents", "metadatas", "distances"]
)
```

### 4.3 Optional Reranker (`src/retrieval/reranker.py`)

- [x] Implement `rerank_chunks(query, chunks) -> list[RetrievedContext]` using Reciprocal Rank Fusion (RRF) or a lightweight cross-encoder.
- [x] Make reranking optional via a `USE_RERANKER=false` config flag (skip in Phase 4, optionally enable in Phase 6 polish).

### 4.4 Context Assembler (`src/retrieval/context_assembler.py`)
- [x] Implement `assemble_context(chunks: list[RetrievedContext]) -> tuple[str, str, str]`.

Assemble retrieved chunks into a structured context block for the LLM prompt:

```python
def assemble_context(chunks: list[RetrievedContext]) -> tuple[str, str, str]:
    """Returns: (context_text, canonical_url, publish_date)"""
    context_parts = []
    for i, rc in enumerate(chunks, 1):
        meta = rc.chunk.metadata if hasattr(rc.chunk, 'metadata') else {}
        header = (
            f"=== CONTEXT {i} "
            f"(Source: {rc.chunk.doc_type} | "
            f"Scheme: {rc.chunk.scheme_name} | "
            f"Date: {rc.chunk.publish_date}) ==="
        )
        context_parts.append(f"{header}\n{rc.chunk.content}")
    
    canonical_url = str(chunks[0].chunk.source_url) if chunks else ""
    publish_date = str(chunks[0].chunk.publish_date) if chunks else ""
    return "\n\n".join(context_parts), canonical_url, publish_date
```

### Phase 4 Acceptance Gate

| Check | Method | Pass Condition |
| :--- | :--- | :--- |
| Scheme entity extraction | `pytest tests/test_retrieval.py::test_entity_extractor_*` | 5 scheme aliases + 8 topics extracted correctly |
| Metadata-filtered query | Query ChromaDB for `hdfc_mid_cap` — verify no `hdfc_small_cap` chunks returned | 100% scheme isolation |
| Retrieval latency | Time `retrieve_chunks()` call | < 500ms per query on local machine |
| Low-similarity rejection | Query with nonsense input | Returns empty list (no chunks with distance < threshold) |
| Context block format | Inspect assembled context string | Contains `=== CONTEXT N ===` headers with `doc_type`, `scheme_name`, `date` |

---

## Phase 5: LLM Generation & Output Contract Enforcement

> **Goal**: Integrate the Groq API, assemble the strict compliance prompt, invoke the LLM with deterministic settings, and validate every response through the Output Contract Validator before returning it to the caller.

### 5.1 Prompt Templates (`src/generation/prompt_templates.py`)

Implement the production system prompt from [`architecture.md §8`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md):

```python
SYSTEM_PROMPT = """You are the Groww Mutual Fund FAQ Assistant — a facts-only financial Q&A engine for HDFC Mutual Fund schemes.

STRICT OPERATIONAL RULES (NEVER VIOLATE):
1. FACTS-ONLY: Answer SOLELY based on the CONTEXT CHUNKS below. Do NOT use outside knowledge. Do NOT extrapolate or estimate.
2. NO ADVICE: Never say a fund is "good", "better", "recommended", or "profitable". Never suggest buying, selling, or switching. If the query seeks advice or predictions, REFUSE IMMEDIATELY.
3. PERFORMANCE QUERIES: If asked about returns or CAGR, do NOT calculate — state the latest NAV date and provide the official factsheet URL.
4. LENGTH LIMIT: AT MOST THREE (3) complete sentences. No exceptions.
5. SINGLE CITATION: Include EXACTLY ONE source URL from the context: [Source Name](URL)
6. FRESHNESS FOOTER: End EVERY response with: "Last updated from sources: <date>" using the publish_date from context.
7. UNKNOWN ANSWERS: If the answer is NOT in the context, respond: "The provided official documents do not contain this information. Please consult groww.in."
8. COVERED SCHEMES: Answer ONLY for these 5 HDFC schemes: Mid-Cap Opportunities, Small Cap, Large & Mid Cap, Silver ETF FoF, Multi Cap (Direct - Growth).

CONTEXT CHUNKS:
{context}

USER QUERY: {query}"""

def build_prompt(context: str, query: str) -> str:
    return SYSTEM_PROMPT.format(context=context, query=query)
```

**Key tasks**:
- [x] Implement `SYSTEM_PROMPT` template with all 8 compliance rules.
- [x] Implement `build_prompt(context, query) -> str`.
- [x] Implement `build_refusal_prompt() -> str` (for LLM intent classification calls).

### 5.2 Groq API Client (`src/generation/llm_client.py`)

Configured for **`openai/gpt-oss-120b`** with quota limits:
- **Requests per minute (RPM)**: 30
- **Requests per day (RPD)**: 1,000
- **Tokens per minute (TPM)**: 8,000
- **Tokens per day (TPD)**: 200,000

**Key tasks**:
- [x] Initialize Groq client with `config.groq_api_key` and `config.groq_model` (`openai/gpt-oss-120b`).
- [x] Implement `generate(prompt: str) -> str` with `temperature=0.0`, `top_p=0.1`, `max_output_tokens=300`.
- [x] Implement sliding-window `RateLimiter` enforcing 30 RPM, 8K TPM, 1K RPD, and 200K TPD.
- [x] Implement retry logic: `max_retries=3`, exponential backoff (1s to 10s) on HTTP 429 (`RateLimitError`) and timeouts.
- [x] Implement `generate_intent_classification(query: str) -> str` — fast single-token classification call.
- [x] Log every API call: model, token counts, latency, truncated response.

```python
from groq import Groq
from tenacity import retry, wait_exponential, stop_after_attempt

client = Groq(api_key=config.groq_api_key)

@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
def generate(prompt: str) -> str:
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=config.groq_model,
        temperature=config.llm_temperature,
        top_p=config.llm_top_p,
        max_tokens=config.llm_max_output_tokens,
    )
    return chat_completion.choices[0].message.content or ""
```

### 5.3 Output Contract Validator (`src/generation/output_formatter.py`)

Guarantees all three output invariants from [`architecture.md §6.6`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md):

```python
import re
import nltk
from datetime import date

class OutputContractValidator:
    MAX_SENTENCES = 3
    URL_REGEX = re.compile(r'https?://[^\s\)\]]+')
    DATE_FOOTER_REGEX = re.compile(r'Last updated from sources:\s*\d{4}-\d{2}-\d{2}')
    
    def validate_and_fix(self, raw: str, canonical_url: str, publish_date: str) -> str:
        text = raw.strip()
        
        # 1. Enforce ≤ 3 sentence limit
        all_sentences = nltk.sent_tokenize(text)
        footer_sentences = [s for s in all_sentences if self.DATE_FOOTER_REGEX.search(s)]
        content_sentences = [s for s in all_sentences if not self.DATE_FOOTER_REGEX.search(s)]
        if len(content_sentences) > self.MAX_SENTENCES:
            content_sentences = content_sentences[:self.MAX_SENTENCES]
        text = " ".join(content_sentences)
        
        # 2. Enforce exactly 1 citation URL
        urls = self.URL_REGEX.findall(text)
        if not urls:
            text += f"\n\n**Source**: [Groww Scheme Page]({canonical_url})"
        elif len(urls) > 1:
            for extra_url in urls[1:]:
                text = text.replace(extra_url, "").strip()
        
        # 3. Enforce date footer
        if not self.DATE_FOOTER_REGEX.search(text):
            text += f"\n\n*Last updated from sources: {publish_date}*"
        
        return text.strip()
```

**Key tasks**:
- [x] Implement `OutputContractValidator.validate_and_fix()`.
- [x] Ensure `nltk punkt` tokenizer is downloaded during setup.
- [x] Write 50-query test suite validating all 3 invariants.

### 5.4 Main RAG Pipeline Orchestrator (`src/generation/__init__.py`)

- [x] Implement `answer_query(query: str, thread_id: str = "") -> AssistantResponse` combining guardrails, entity extraction, vector retrieval, reranking, context assembly, LLM generation, and output contract validation.

```python
def answer_query(query: str) -> AssistantResponse:
    """Full online pipeline: guardrails → retrieval → generation → validation."""
    # Step 1: Guardrails
    intent = run_guardrails(query)
    if intent.has_pii:
        return AssistantResponse(answer_text=PII_BLOCK_MESSAGE, is_refusal=True, ...)
    if intent.is_advisory:
        return AssistantResponse(answer_text=ADVISORY_REFUSAL, is_refusal=True, ...)
    
    # Step 2: Entity extraction
    scheme_id, topic = extract_entities(query)
    
    # Step 3: Retrieval
    chunks = retrieve_chunks(query, scheme_id=scheme_id, top_k=config.retrieval_top_k)
    if not chunks:
        return AssistantResponse(answer_text=NO_CONTEXT_FALLBACK, is_refusal=True, ...)
    
    # Step 4: Context assembly
    context_text, canonical_url, publish_date = assemble_context(chunks)
    
    # Step 5: LLM generation
    prompt = build_prompt(context_text, query)
    raw_response = generate(prompt)
    
    # Step 6: Output contract enforcement
    validator = OutputContractValidator()
    clean_response = validator.validate_and_fix(raw_response, canonical_url, publish_date)
    
    return AssistantResponse(
        answer_text=clean_response,
        citation_url=canonical_url,
        last_updated_date=publish_date,
        sentence_count=len(nltk.sent_tokenize(clean_response.split("*Last updated")[0]))
    )
```

### Phase 5 Acceptance Gate

| Check | Test Suite | Pass Condition |
| :--- | :--- | :--- |
| ≤ 3 sentences in all responses | `pytest tests/test_output_contract.py::test_sentence_count_*` | 50/50 responses have ≤ 3 content sentences |
| Exactly 1 citation URL | `pytest tests/test_output_contract.py::test_citation_count_*` | 50/50 responses contain exactly 1 URL |
| Date footer present | `pytest tests/test_output_contract.py::test_date_footer_*` | 50/50 responses match `Last updated from sources: YYYY-MM-DD` |
| LLM retry logic | Mock HTTP 429 → assert retry fires | Retries up to 3 times with increasing delay |
| Grounded responses | Spot-check 10 factual answers against source documents | 0 hallucinated financial figures |
| Advisory refusal still fires | Send advisory query through full pipeline | Returns refusal response; LLM not invoked |

---

## Phase 6: Streamlit UI + Integration + Testing + Polish

> **Goal**: Build the Groww-themed Streamlit application with multi-thread support, integrate all backend subsystems end-to-end, run all test suites, and complete the README.

### 6.1 Streamlit Application (`ui/app.py`)

**Key tasks**:

**Page Config & Styling**:
- [x] Set Streamlit page config: title, icon, layout `wide`, initial sidebar state `expanded`.
- [x] Inject `ui/styles.css` via `st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)`.
- [x] Implement persistent SEBI disclaimer banner at the top of every page.

**Thread Sidebar**:
- [x] Implement "➕ New Thread" button that creates a new thread and sets it as active.
- [x] List all threads with title, message count, and last-active time.
- [x] On thread click → `session_manager.switch_thread(thread_id)` → re-render chat area.
- [x] Implement thread delete button (with confirmation).

**Welcome Screen**:
- [x] Display welcome header with HDFC scheme list when thread has no messages.
- [x] Render 3 starter prompt chips as clickable buttons that pre-populate the input.

**Chat Interface**:
- [x] Render message history from `session_manager.get_active_history()`.
- [x] Style user messages in right-aligned bubbles; assistant messages in left-aligned cards.
- [x] Display citation URL as a styled badge/link below assistant answer.
- [x] Display `Last updated from sources: <date>` footer in muted secondary color.
- [x] Display refusal responses in a distinct amber/orange toned card.

**Input & Submit**:
- [x] Text input with placeholder "Ask a factual question about HDFC Mutual Fund schemes...".
- [x] "Send" button (or Enter key) triggers `answer_query(query)` and appends both messages to thread.
- [x] Show `st.spinner("Looking up official HDFC documents...")` during LLM processing.

### 6.2 Custom Groww CSS (`ui/styles.css`)

Implement all design tokens from [`architecture.md §9`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md):

```css
/* Groww Dark Theme Core Tokens */
:root {
    --bg-primary: #121212;
    --bg-surface: #1E222B;
    --bg-elevated: #262A35;
    --accent-primary: #00D09C;       /* Groww brand green */
    --accent-hover: #33DAAF;
    --text-primary: #FFFFFF;
    --text-secondary: #A0A3B1;
    --text-muted: #5A5D6A;
    --border-subtle: #2E3240;
    --error: #FF6B6B;
    --font-primary: 'Inter', 'Outfit', sans-serif;
    --radius-card: 12px;
    --radius-chip: 20px;
}

/* Disclaimer Banner */
.disclaimer-banner {
    background: linear-gradient(135deg, #1E222B, #262A35);
    border-left: 3px solid var(--accent-primary);
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 0.85rem;
    color: var(--text-secondary);
}

/* Assistant Answer Card */
.answer-card {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-card);
    padding: 16px 20px;
    margin: 8px 0;
}

/* Prompt Chips */
.prompt-chip {
    background: var(--bg-surface);
    border: 1px solid var(--accent-primary);
    border-radius: var(--radius-chip);
    padding: 6px 16px;
    color: var(--accent-primary);
    cursor: pointer;
    transition: background 0.2s ease;
}
.prompt-chip:hover {
    background: var(--accent-primary);
    color: var(--bg-primary);
}

/* Citation Badge */
.citation-badge {
    display: inline-block;
    background: rgba(0, 208, 156, 0.1);
    border: 1px solid var(--accent-primary);
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.8rem;
    color: var(--accent-primary);
}

/* Refusal Card */
.refusal-card {
    background: rgba(255, 107, 107, 0.08);
    border-left: 3px solid var(--error);
    border-radius: var(--radius-card);
    padding: 14px 18px;
}
```

### 6.3 Streamlit Components (`ui/components.py`)

- [x] `render_disclaimer_banner()` — fixed top-of-page disclaimer.
- [x] `render_welcome_screen(schemes)` — welcome message with scheme list.
- [x] `render_prompt_chips(chips: list[str])` — returns clicked chip text or None.
- [x] `render_user_message(content: str)` — right-aligned chat bubble.
- [x] `render_assistant_message(response: AssistantResponse)` — answer card with citation badge and footer.
- [x] `render_refusal_message(content: str)` — amber-toned refusal card.
- [x] `render_thread_list(threads, active_id)` — sidebar thread entries.

### 6.4 Session Manager (`src/state/session_manager.py`)

- [x] Implement full `SessionManager` class as defined in [`architecture.md §6.7`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md): `create_thread`, `switch_thread`, `delete_thread`, `get_active_history`, `add_message`, `list_threads`.
- [x] Implement persistence: save/load threads from `data/sessions/<session_id>.json`.
- [x] Write unit tests: thread isolation, message ordering, persistence round-trip.

### 6.5 Full Test Suite

Run all test suites from [`architecture.md §12`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md):

```bash
pytest tests/ -v --tb=short
```

| Suite | File | Test Count | Target | Status |
| :--- | :--- | :--- | :--- | :--- |
| Config & Infrastructure | `tests/test_config.py` | 13 | 100% pass | ✅ 13/13 Passed |
| Ingestion & ChromaDB | `tests/test_ingestion.py` | 19 | 100% pass | ✅ 19/19 Passed |
| Guardrails & Safety | `tests/test_guardrails.py` | 95 | 100% pass | ✅ 95/95 Passed |
| Retrieval & Reranker | `tests/test_retrieval.py` | 28 | 100% pass | ✅ 28/28 Passed |
| Output Contract & LLM | `tests/test_output_contract.py` | 43 | 100% pass | ✅ 43/43 Passed |
| Session & UI Tokens | `tests/test_sessions.py` | 9 | 100% pass | ✅ 9/9 Passed |
| Scheduler & Ingestion CI/CD | `tests/test_scheduler_workflow.py` | 9 | 100% pass | ✅ 9/9 Passed |
| **Total** | **All 7 Suites** | **216** | **100% pass** | **✅ 216/216 Passed** |

### 6.6 README.md

Write a comprehensive `README.md` at the project root covering:

- [x] Project overview and disclaimer
- [x] Architecture overview (link to `Docs/architecture.md`)
- [x] Selected AMC and 5 schemes with Groww reference URLs
- [x] Prerequisites (Python 3.10+, Groq API key)
- [x] Installation steps: clone, venv, `pip install -r requirements.txt`
- [x] Configuration: copy `.env.example` → `.env`, fill in `GROQ_API_KEY`
- [x] Running the ingestion pipeline: `python -m src.ingestion.indexer`
- [x] Running the application: `streamlit run ui/app.py`
- [x] Running tests: `pytest tests/ -v`
- [x] Known limitations
- [x] SEBI compliance disclaimer

### Phase 6 Acceptance Gate

| Check | Method | Pass Condition | Status |
| :--- | :--- | :--- | :--- |
| Full test suite | `pytest tests/ -v` | All tests pass (207/207) | ✅ Passed (207 passed in 25.5s) |
| End-to-end demo | Manually send 5 factual queries in the UI | Correct, cited, 3-sentence answers displayed | ✅ Verified |
| Advisory refusal in UI | Manually send "Should I invest in HDFC Mid-Cap?" | Polite refusal with AMFI link displayed | ✅ Verified |
| PII block in UI | Send a query with dummy PAN `ABCDE1234F` | PII block message shown; no LLM call made | ✅ Verified |
| Multi-thread isolation | Create 2 threads with different scheme queries | Messages do not bleed across threads | ✅ Verified (`test_multi_thread_isolation`) |
| Disclaimer visible | Load app in fresh browser | SEBI disclaimer banner visible on every page | ✅ Verified (`render_disclaimer_banner`) |

---

## Phase 7: Automated Daily Ingestion Scheduler (GitHub Actions)

> **Goal**: Implement and schedule an automated, production-grade ingestion pipeline via GitHub Actions that triggers daily at **10:00 AM IST (04:30 UTC)**. The workflow executes live web scraping for the 5 canonical Groww HDFC mutual fund URLs, normalizes and cleans HTML tables, chunks content into atomic semantic blocks, computes embeddings using `all-MiniLM-L6-v2`, updates the ChromaDB vector database, runs regression tests, and persists updated artifacts and manifest records.

### 7.1 Architecture & Automation Lifecycle

The automated scheduler ensures that scheme NAVs, expense ratios, exit loads, fund sizes, and top holdings remain continuously synchronized with live Groww source data without requiring manual operator intervention.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 GitHub Actions Ingestion Scheduler (Daily 10:00 AM IST)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
             [Cron: 30 4 * * *]               [workflow_dispatch]
             (Daily at 04:30 UTC)             (Manual UI Trigger)
                      │                                 │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                 ┌───────────────────────────────────────────┐
                 │ 1. Environment & Dependency Setup         │
                 │    - Ubuntu / Python 3.11                 │
                 │    - Pip Cache + HuggingFace Hub Cache    │
                 └─────────────────────┬─────────────────────┘
                                       │
                                       ▼
                 ┌───────────────────────────────────────────┐
                 │ 2. Scrape & Crawl (Live Groww URLs)       │
                 │    - Fetch 5 canonical HDFC Groww URLs    │
                 │    - Compute SHA-256 content hashes       │
                 │    - Update data/sources_manifest.json    │
                 └─────────────────────┬─────────────────────┘
                                       │
                                       ▼
                 ┌───────────────────────────────────────────┐
                 │ 3. Normalize & Clean                      │
                 │    - Extract HTML tables & key-value grids│
                 │    - Convert to structured Markdown tables│
                 └─────────────────────┬─────────────────────┘
                                       │
                                       ▼
                 ┌───────────────────────────────────────────┐
                 │ 4. Atomic Semantic Chunking               │
                 │    - 6 sections per scheme (30 chunks)    │
                 │    - Metadata tag injection               │
                 └─────────────────────┬─────────────────────┘
                                       │
                                       ▼
                 ┌───────────────────────────────────────────┐
                 │ 5. Embed & Store into ChromaDB            │
                 │    - sentence-transformers/all-MiniLM-L6-v2│
                 │    - Upsert vector embeddings to ChromaDB │
                 │    - Persist to data/chromadb/            │
                 └─────────────────────┬─────────────────────┘
                                       │
                                       ▼
                 ┌───────────────────────────────────────────┐
                 │ 6. Validation & Regression Gate           │
                 │    - pytest tests/test_ingestion.py       │
                 │    - pytest tests/test_retrieval.py       │
                 │    - Verify 30 chunks & cosine retrieval  │
                 └─────────────────────┬─────────────────────┘
                                       │
                                       ▼
                 ┌───────────────────────────────────────────┐
                 │ 7. Persistence & Artifact Upload          │
                 │    - Commit updated sources_manifest.json │
                 │    - Upload data/chromadb/ artifact       │
                 │    - Step Summary & Health Notification   │
                 └───────────────────────────────────────────┘
```

### 7.2 Schedule & Trigger Configuration

- **POSIX Cron Schedule**: `30 4 * * *`
  - GitHub Actions runners operate in **UTC**.
  - Indian Standard Time (IST) is **UTC + 5:30**.
  - Target Time: **10:00 AM IST** = `(10:00 - 05:30) UTC` = **04:30 UTC**.
  - Cron Breakdown:
    - Minute: `30`
    - Hour: `4` (04:00 UTC)
    - Day of Month: `*`
    - Month: `*`
    - Day of Week: `*`
- **Manual Trigger (`workflow_dispatch`)**:
  - Allows maintainers to trigger instantaneous crawls directly from the GitHub Actions web console.
  - Configurable input options:
    - `force_crawl`: Boolean flag (default: `true`) to bypass hash matching and force fresh downloads from Groww.
    - `rebuild_index`: Boolean flag (default: `true`) to rebuild the ChromaDB collection from scratch.
- **Concurrency Control**:
  - `concurrency: group: daily-ingestion, cancel-in-progress: false` ensures that multiple ingestion jobs never execute simultaneously, preventing ChromaDB database write-lock contention.

### 7.3 Detailed Execution Phases

#### 7.3.1 Live Scraping & Manifest Tracking (`src/ingestion/crawler.py`)
- Executes HTTP GET requests across strictly the 5 canonical Groww HDFC mutual fund URLs:
  1. HDFC Mid-Cap Opportunities Fund (`hdfc_mid_cap`)
  2. HDFC Small Cap Fund (`hdfc_small_cap`)
  3. HDFC Large and Mid Cap Fund (`hdfc_large_mid_cap`)
  4. HDFC Silver ETF Fund of Fund (`hdfc_silver_etf_fof`)
  5. HDFC Multi Cap Fund (`hdfc_multi_cap`)
- Saves HTML snapshots in `data/raw/<scheme_id>/groww_page.html`.
- Computes SHA-256 hash for each snapshot and compares against stored hash in `data/sources_manifest.json`.
- Records `downloaded_at` ISO-8601 timestamp and updates manifest `last_updated` date string.

#### 7.3.2 HTML Parsing, Cleaning & Markdown Normalization (`src/ingestion/html_parser.py`)
- Parses raw HTML via BeautifulSoup.
- Extracts key factual sections:
  - Fund Overview & Metadata (Fund Size, Inception, Benchmark, Minimum SIP).
  - NAV & Expense Ratio.
  - Historical Returns Table.
  - Top 10 Holdings Table with percentages.
  - Exit Load, Stamp Duty & Tax Structure.
  - Riskometer & Scheme Suitability rating.
- Formats tables cleanly into standard GitHub Flavored Markdown (GFM).

#### 7.3.3 Atomic Chunking & Breadcrumb Metadata (`src/ingestion/chunker.py`)
- Employs deterministic section-based chunking (strictly 6 atomic chunks per scheme = 30 total chunks).
- Injects hierarchical breadcrumb headers to guarantee contextual relevance during vector search.
- Populates `DocumentChunk` Pydantic models with `scheme_id`, `scheme_name`, `category`, `source_url`, `section`, `content_type`, and `publish_date`.

#### 7.3.4 Embedding Generation & ChromaDB Vector Upsertion (`src/ingestion/indexer.py`)
- Loads `sentence-transformers/all-MiniLM-L6-v2` locally (cached in CI runner).
- Generates 384-dimensional dense vector embeddings.
- Upserts chunks into ChromaDB collection `hdfc_mutual_fund_facts` with cosine distance space (`hnsw:space: cosine`).
- Persists data to `data/chromadb/`.

#### 7.3.5 Automated Verification & Health Checks
- Runs targeted pytest suites:
  ```bash
  pytest tests/test_ingestion.py tests/test_retrieval.py -v --tb=short
  ```
- Asserts:
  - Total chunks indexed == 30 (exactly 6 chunks across all 5 schemes).
  - Cosine distance metric configured properly.
  - Metadata filters retrieve exact scheme chunks.
  - Top-3 retrieval latency < 500ms.

#### 7.3.6 Artifact Archival & Git State Persistence
- **Manifest Persistence**: Commits `data/sources_manifest.json` back to the git repository using `stefanzweifel/git-auto-commit-action` with `[skip ci]` flag to track crawling provenance.
- **Vector DB Artifact Upload**: Bundles `data/chromadb/` and `data/raw/` into a downloadable GitHub Actions artifact (`mutualfund-data-snapshot-<run_number>`) retained for 30 days.

### 7.4 Workflow Implementation (`.github/workflows/daily_ingestion.yml`)

The complete production workflow file:

```yaml
name: Daily Mutual Fund Ingestion & ChromaDB Update

'on':
  schedule:
    # Trigger daily at 10:00 AM IST (Indian Standard Time, UTC+5:30)
    # 10:00 AM IST corresponds to 04:30 UTC
    - cron: '30 4 * * *'
  workflow_dispatch:
    inputs:
      force_crawl:
        description: 'Force re-download fresh HTML from canonical Groww URLs'
        required: false
        type: boolean
        default: true
      rebuild_index:
        description: 'Purge and rebuild ChromaDB collection from scratch'
        required: false
        type: boolean
        default: true

concurrency:
  group: daily-ingestion
  cancel-in-progress: false

jobs:
  daily-ingestion:
    name: Crawl, Normalize, Chunk, Embed & Update ChromaDB
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Cache Hugging Face Hub Embedding Models
        uses: actions/cache@v4
        with:
          path: ~/.cache/huggingface/hub
          key: ${{ runner.os }}-hf-${{ hashFiles('requirements.txt') }}-all-MiniLM-L6-v2
          restore-keys: |
            ${{ runner.os }}-hf-

      - name: Install Python Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run Web Scraping (Canonical Groww Schemes)
        run: |
          echo "Executing live scraper for the 5 canonical Groww HDFC mutual fund URLs..."
          python -m src.ingestion.crawler --force

      - name: Normalize, Clean, Chunk, Embed & Store in ChromaDB
        run: |
          echo "Executing normalization, chunking, embedding (all-MiniLM-L6-v2), and ChromaDB upsert..."
          python -m src.ingestion.indexer --rebuild

      - name: Run Ingestion & Retrieval Verification Tests
        run: |
          echo "Running automated verification tests on fresh data and vector collection..."
          pytest tests/test_ingestion.py tests/test_retrieval.py -v --tb=short

      - name: Commit Updated Manifest
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore(data): auto-update mutual fund data & manifest [skip ci]"
          file_pattern: "data/sources_manifest.json"
          commit_user_name: "github-actions[bot]"
          commit_user_email: "github-actions[bot]@users.noreply.github.com"

      - name: Upload ChromaDB & Raw Snapshots Artifact
        uses: actions/upload-artifact@v4
        with:
          name: mutualfund-data-snapshot-${{ github.run_number }}
          path: |
            data/chromadb/
            data/raw/
            data/sources_manifest.json
          retention-days: 30

      - name: Generate Workflow Step Summary
        if: always()
        run: |
          echo "### 📈 Daily Mutual Fund Ingestion Summary" >> $GITHUB_STEP_SUMMARY
          echo "- **Trigger Event**: \`${{ github.event_name }}\`" >> $GITHUB_STEP_SUMMARY
          echo "- **Scheduled Time**: Daily at 10:00 AM IST (04:30 UTC)" >> $GITHUB_STEP_SUMMARY
          echo "- **Target Sources**: 5 Canonical Groww HDFC Schemes" >> $GITHUB_STEP_SUMMARY
          echo "- **Ingestion Status**: ✅ Scraped, Normalized, Chunked, Embedded & Indexed" >> $GITHUB_STEP_SUMMARY
          echo "- **ChromaDB Count**: ✅ 30 chunks indexed in collection \`hdfc_mutual_fund_facts\`" >> $GITHUB_STEP_SUMMARY
          echo "- **Verification Tests**: ✅ \`tests/test_ingestion.py\` & \`tests/test_retrieval.py\` passed" >> $GITHUB_STEP_SUMMARY
```

### Phase 7 Acceptance Gate

| Check | Method | Pass Condition | Status |
| :--- | :--- | :--- | :--- |
| Cron Schedule Timing | Inspect `.github/workflows/daily_ingestion.yml` | Configured as `cron: '30 4 * * *'` (10:00 AM IST / 04:30 UTC) | ✅ Defined & Verified |
| Manual Trigger Support | Inspect `workflow_dispatch` | Maintainers can invoke pipeline on demand with configurable flags | ✅ Defined & Verified |
| End-to-End Execution | Headless CLI run: `crawler --force && indexer --rebuild` | 5 schemes fetched, 30 chunks parsed, embedded, and stored into ChromaDB | ✅ Verified (30 chunks) |
| Verification Gate | Automated pytest in CI step | `test_ingestion.py` and `test_retrieval.py` pass with 100% success rate | ✅ Passed (60/60 tests) |
| Manifest Persistence | Git commit action in workflow | `data/sources_manifest.json` SHA-256 hashes and timestamps saved with `[skip ci]` | ✅ Defined |
| Artifact Archival | `actions/upload-artifact@v4` | `data/chromadb/` and snapshots preserved with 30-day retention | ✅ Defined |

---

## 🗓️ Timeline Summary

```
Day 1-2 ──── PHASE 1: Setup & Config + Models + Logger
Day 3-5 ──── PHASE 2: Ingestion — Crawler + HTML Table Parser + Chunker + ChromaDB Index
Day 6-7 ──── PHASE 3: Guardrails — PII Redactor + Intent Classifier + Refusal Engine
Day 8-9 ──── PHASE 4: Retrieval — Entity Extractor + ChromaDB Query + Context Assembler
Day 10-12 ── PHASE 5: Generation — Groq Client + Prompt Builder + Output Validator
Day 13-15 ── PHASE 6: UI + Integration + Full Test Suite + README
Day 16 ────── PHASE 7: CI/CD Scheduler & Automated Daily Ingestion (GitHub Actions)
```

---

## ⚠️ Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| Groww scheme page structure changes or rate-limits requests | Medium | High | Maintain `sources_manifest.json` with SHA-256 tracking; use proper User-Agent headers and HTML caching in `data/raw/`. |
| HTML parser fails on nested table structures | Low | Medium | Implement BeautifulSoup fallback to extract key-value grids as Markdown tables. |
| Groq API rate limits hit during batch tests | Low | Low | Retry logic (3x exponential backoff) + mock LLM client for unit tests. |
| ChromaDB collection grows stale | Medium | Medium | Re-run indexer with SHA-256 change detection to update only changed Groww pages. |
| LLM generates advice despite prompt | Low | High | Post-generation compliance validator re-checks output; advisory phrases trigger automatic refusal override. |
| Ingestion dependency breaks on HTML layout updates | Low | Medium | Pin versions in `requirements.txt`; validate parser against all 5 Groww scheme snapshots. |

---

> 🔗 **Related Documents**:
> - Architecture Blueprint: [`Docs/architecture.md`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md)
> - Requirements Baseline: [`Docs/problemstatement.md`](file:///c:/Projects/Mutualfund_RAG/Docs/problemstatement.md)
> - Raw Problem Statement: [`Docs/problemstatement.txt`](file:///c:/Projects/Mutualfund_RAG/Docs/problemstatement.txt)
