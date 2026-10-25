# Groww HDFC Mutual Fund Facts Assistant 📈

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit App](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg)](https://streamlit.io/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5+-orange.svg)](https://www.trychroma.com/)
[![Groq LLM](https://img.shields.io/badge/Groq-openai%2Fgpt--oss--120b-green.svg)](https://groq.com/)
[![Tests Passing](https://img.shields.io/badge/Tests-227%20Passed-brightgreen.svg)](tests/)
[![Design System](https://img.shields.io/badge/Design-Groww%20Obsidian%20Emerald-00D09C.svg)](stitch/obsidian_emerald/DESIGN.md)

> **SEBI Regulatory Compliance & Facts-Only Policy**:
> This application is an educational, facts-only financial Q&A engine strictly grounded in certified scheme factsheets for **5 HDFC Mutual Fund schemes**. It strictly **prohibits investment advice, fund recommendations, performance predictions, and comparative analysis**. All advisory and PII queries trigger automated compliance refusals with educational redirects to [AMFI](https://www.amfiindia.com/investor-corner/knowledge-center) and [SEBI](https://www.sebi.gov.in/investor.html).

---

## 📑 Table of Contents
1. [Project Overview](#-project-overview)
2. [Covered Schemes & Sources](#-covered-schemes--sources)
3. [Architecture & Technical Specifications](#-architecture--technical-specifications)
4. [Strict Operational Invariants](#-strict-operational-invariants)
5. [Prerequisites](#-prerequisites)
6. [Installation & Setup](#-installation--setup)
7. [Environment Configuration](#-environment-configuration)
8. [Ingestion Pipeline Execution](#-ingestion-pipeline-execution)
9. [Running the Streamlit UI](#-running-the-streamlit-ui)
10. [Test Suite Execution](#-test-suite-execution)
11. [Session Management & Multi-Thread Isolation](#-session-management--multi-thread-isolation)
12. [UI Design & Anti-Overflow Protections](#-ui-design--anti-overflow-protections)
13. [Known Limitations & Disclaimers](#-known-limitations--disclaimers)

---

## 🌟 Project Overview

The **Groww HDFC Mutual Fund Facts Assistant** delivers verified, deterministic answers to user queries regarding Total Expense Ratios (TER), exit loads, minimum SIP/lumpsum amounts, lock-in periods, benchmark indices, fund managers, and portfolio allocations.

Built with a production-grade **Retrieval-Augmented Generation (RAG)** pipeline, it features:
- **Two-Tier Guardrails**: Real-time regex and entity interception for Indian financial PII (PAN, Aadhaar, Folio, Bank accounts) and regex/LLM fast-path blocking for advisory queries.
- **Section-Atomic Chunking**: Grounded in empirical data research, preserving tables without row severing.
- **Local Dense Vector Retrieval**: Zero external embedding latency with `sentence-transformers/all-MiniLM-L6-v2` and `ChromaDB` cosine filtering.
- **Enterprise LLM Integration**: Powered by Groq's `openai/gpt-oss-120b` with client-side sliding-window rate limiters (30 RPM, 8K TPM, 1K RPD, 200K TPD) and exponential backoff retry logic.
- **Rigid Output Contract**: Strict enforcement of $\le 3$ sentences, exactly 1 citation URL, and a statutory freshness date footer.
- **Obsidian Emerald Dark Theme UI**: Built with Streamlit, styled with Groww dark-mode tokens, featuring multi-thread isolation, thread deletion, starter prompt chips, and anti-overflow responsive layouts.

---

## 🏛️ Covered Schemes & Sources

The corpus is strictly constrained to **5 canonical HDFC Mutual Fund Direct-Growth schemes** fetched directly from Groww:

| Scheme ID | Scheme Name | Plan / Option | Canonical Groww Factsheet URL |
| :--- | :--- | :--- | :--- |
| `hdfc_mid_cap` | **HDFC Mid-Cap Opportunities Fund** | Direct Plan - Growth | [Groww Mid-Cap Page](https://groww.in/mutual-funds/hdfc-mid-cap-opportunities-fund-direct-growth) |
| `hdfc_small_cap` | **HDFC Small Cap Fund** | Direct Plan - Growth | [Groww Small Cap Page](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth) |
| `hdfc_large_mid_cap` | **HDFC Large and Mid Cap Fund** | Direct Plan - Growth | [Groww Large & Mid Cap Page](https://groww.in/mutual-funds/hdfc-large-and-mid-cap-fund-direct-growth) |
| `hdfc_silver_etf_fof` | **HDFC Silver ETF Fund of Fund** | Direct Plan - Growth | [Groww Silver ETF FoF Page](https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth) |
| `hdfc_multi_cap` | **HDFC Multi Cap Fund** | Direct Plan - Growth | [Groww Multi Cap Page](https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth) |

> **Strict Scope Boundary**: No extra URLs, third-party blogs, or unverified AMC sub-pages are indexed.

---

## 🏗️ Architecture & Technical Specifications

```
                                  [ User Query ]
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │    Stage 1: Safety & Guardrail Gate   │
                     ├───────────────────────────────────────┤
                     │ • PII Redactor (PAN, Aadhaar, Folio)  │──► [ PII Refusal ]
                     │ • Intent Classifier (Regex + LLM)     │──► [ Advisory Refusal ]
                     └───────────────────────────────────────┘
                                         │ (Factual Allowed)
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ Stage 2: Entity & Retrieval Pipeline  │
                     ├───────────────────────────────────────┤
                     │ • Entity Extractor (Scheme & Topic)   │
                     │ • ChromaDB Cosine Search (Top-3)      │
                     │ • Low-Confidence Rejection (Dist>0.65)│
                     │ • Reciprocal Rank Fusion (Optional)   │
                     │ • Context Assembler                   │
                     └───────────────────────────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │   Stage 3: LLM & Contract Validator   │
                     ├───────────────────────────────────────┤
                     │ • Groq LLM: openai/gpt-oss-120b       │
                     │ • Deterministic Gen: Temp=0, Top_p=0.1│
                     │ • Rate Limiter: 30 RPM, 8K TPM        │
                     │ • Output Contract Validator:          │
                     │   1. ≤ 3 Sentences                    │
                     │   2. Exactly 1 Citation URL           │
                     │   3. Last updated: YYYY-MM-DD         │
                     └───────────────────────────────────────┘
                                         │
                                         ▼
                     [ Rendered UI Card with Groww Obsidian Theme ]
```

- **Architecture Details**: See [`Docs/architecture.md`](Docs/architecture.md).
- **Implementation Verification**: See [`Docs/implementation-plan.md`](Docs/implementation-plan.md).

---

## 🔒 Strict Operational Invariants

Every response returned by the assistant satisfies three inviolable contracts:
1. **Length Limit**: Exactly $\le 3$ complete sentences.
2. **Single Citation**: Exactly 1 citation URL pointing to the relevant Groww scheme page.
3. **Freshness Timestamp**: Mandatory footer `Last updated from sources: YYYY-MM-DD` matching statutory document timestamps.
4. **Zero Advice**: Immediate routing to standardized SEBI/AMFI educational templates when queries ask *"Should I buy?"*, *"Which fund is better?"*, or request return predictions.

---

## 💻 Prerequisites

- **Python**: Version `3.10` or higher (verified on Python 3.11).
- **Groq API Key**: Free or Tier-1 API key from [Groq Console](https://console.groq.com/).
- **Operating System**: Windows, macOS, or Linux.

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/snigdhapanda1410/Mutualfund_RAG.git
cd Mutualfund_RAG
```

### 2. Create and Activate Virtual Environment
On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the root directory by copying `.env.example`:

```bash
cp .env.example .env
```

Configure your environment variables in `.env`:

```ini
# LLM Configuration (Groq)
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
LLM_TEMPERATURE=0.0
LLM_TOP_P=0.1
LLM_MAX_OUTPUT_TOKENS=300

# ChromaDB & Vector Storage
CHROMA_PERSIST_DIRECTORY=./data/chromadb
CHROMA_COLLECTION_NAME=hdfc_mutual_fund_facts
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
RETRIEVAL_TOP_K=3
SIMILARITY_THRESHOLD=0.65
USE_RERANKER=false

# Output Contract Enforcement
MAX_OUTPUT_SENTENCES=3
ENFORCE_SINGLE_CITATION=true

# Application & Regulatory Compliance
SEBI_DISCLAIMER_TEXT=Facts-only. No investment advice.
APP_TITLE=Groww | Mutual Fund FAQ Assistant
SESSION_PERSIST_PATH=./data/sessions/
LOG_LEVEL=INFO
```

---

## 📥 Ingestion Pipeline Execution

The offline ingestion pipeline crawls the 5 Groww URLs, extracts clean Next.js hydration tables, generates section-atomic chunks, and indexes them into ChromaDB:

```bash
# Run idempotent indexing (skips already indexed pages via SHA-256):
python -m src.ingestion.indexer

# Force re-download and re-index from scratch:
python -m src.ingestion.indexer --rebuild --force-crawl

# Automated Daily Ingestion Scheduler:
# Configured via GitHub Actions (.github/workflows/daily_ingestion.yml)
# Triggers daily at 10:00 AM IST (04:30 UTC) to crawl, normalize, chunk, embed, and update ChromaDB.
```

### Corpus Index Metrics
- **Total Chunks**: Exactly 30 atomic chunks (6 sections $\times$ 5 schemes).
- **Chunk Types**: 25 structured financial tables + 5 investment strategy texts.
- **Average Chunk Size**: 184.2 tokens (100% fitting within `all-MiniLM-L6-v2`'s 256-token context).

---

## 🖥️ Running the Streamlit UI

Launch the Groww Obsidian Emerald dark mode user interface:

```bash
streamlit run ui/app.py
```

The application will open locally in your browser at `http://localhost:8501`.

### Key Features in the Interface:
- **Persistent SEBI Compliance Banner**: Constant regulatory disclosure on every screen.
- **5 Scheme Snapshot Cards**: Real-time display of NAV, Direct TER, Exit Load, and Fund Size.
- **Popular Factual Chips**: One-click quick prompts for exit loads, TERs, SIP minimums, and lock-in periods.
- **Multi-Thread Sidebar**: Create new conversation threads, switch between sessions, or delete completed threads.
- **Compliant Response Cards**: Distinct emerald-bordered cards for verified answers and amber-toned alert cards for guardrail refusals.

---

## 🧪 Test Suite Execution

Run the complete, automated test suite covering all 6 phases:

```bash
# Run all 207 tests
pytest tests/ -v

# Run with summary statistics
pytest tests/ -v --tb=short
```

### Test Breakdown by Subsystem:
| Phase | Test Suite File | Coverage Scope | Tests | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | `tests/test_config.py` | Config parsing, env fallback, logger format | 13 | ✅ Passed |
| **Phase 2** | `tests/test_ingestion.py` | Crawler hashes, HTML table parser, chunker, ChromaDB | 19 | ✅ Passed |
| **Phase 3** | `tests/test_guardrails.py` | PII redactor (PAN, Aadhaar), Advisory classifier | 95 | ✅ Passed |
| **Phase 4** | `tests/test_retrieval.py` | Entity extractor, ChromaDB filter, RRF reranker | 28 | ✅ Passed |
| **Phase 5** | `tests/test_output_contract.py` | Contract validator, Groq client, 50 golden queries | 43 | ✅ Passed |
| **Phase 6** | `tests/test_sessions.py` | Session manager, thread isolation, Groww CSS tokens | 9 | ✅ Passed |
| **Phase 7** | `tests/test_scheduler_workflow.py` | GitHub Actions workflow, cron timing (10 AM IST), CI/CD pipeline | 9 | ✅ Passed |
| **Deployment** | `tests/test_api_endpoints.py` | FastAPI REST endpoints, Railway/Vercel config, frontend artifacts | 11 | ✅ Passed |
| **Total** | **All 8 Suites** | **End-to-End System Verification** | **227** | **100% Pass** |

---

## 🧵 Session Management & Multi-Thread Isolation

All conversation sessions are managed via `SessionManager` in `src/state/session_manager.py`:
- **Isolation**: Each thread maintains an independent message history; queries and answers in Thread A never bleed into Thread B.
- **Disk Persistence**: Sessions are saved as JSON files in `data/sessions/<thread_id>.json` and automatically reloaded across application restarts.
- **Automatic Titling**: The first user prompt dynamically updates the thread title from "New Conversation" to the query topic.
- **Recency Ordering**: The sidebar orders threads dynamically by `last_active` timestamp.

---

## 🎨 UI Design & Anti-Overflow Protections

The UI implements the **Groww Obsidian Emerald** design system (`stitch/obsidian_emerald/DESIGN.md`):

### Color Tokens
- **Background Obsidian**: `#121212`
- **Surface Slate**: `#1E222B`
- **Elevated Canvas**: `#262A35`
- **Groww Neon Emerald**: `#00D09C` (Hover: `#33DAAF`)
- **Text Primary**: `#FFFFFF` (WCAG Contrast: 15.3:1)
- **Text Secondary**: `#A0A3B1` (WCAG Contrast: 7.2:1)
- **Compliance Alert**: `#FF6B6B`

### Anti-Overflow Safeguards
In adherence to design feedback from earlier prototype mockups:
1. **Fluid Responsive Grid**: Replaced rigid column spans with CSS Grid `repeat(auto-fit, minmax(220px, 1fr))` ensuring scheme cards never break out of boundaries.
2. **Word-Break Protection**: Enforced `box-sizing: border-box`, `word-break: break-word`, and `overflow-wrap: break-word` across all text blocks, message cards, and metric rows.
3. **Multiline Button Wrapping**: Custom Streamlit button overrides with `white-space: normal !important` and flex layouts prevent prompt chips and sidebar labels from truncating awkwardly with ellipses.

---

## ⚠️ Known Limitations & Disclaimers

1. **Facts-Only Scope**: The assistant does not provide financial planning, portfolio suitability analysis, or tax advice under Section 80C.
2. **Fixed 5 Schemes**: Inquiries concerning schemes outside the 5 designated HDFC Direct-Growth funds are politely refused.
3. **Statutory Historical Data**: Portfolio allocations, NAVs, and expense ratios reflect the statutory dates recorded in the Groww snapshot files.
4. **SEBI Disclaimer**: Mutual fund investments are subject to market risks. Read all scheme-related documents carefully before investing.
