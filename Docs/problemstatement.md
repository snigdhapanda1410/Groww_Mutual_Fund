# 📑 Problem Statement: Mutual Fund FAQ Assistant (Facts-Only Q&A)

> **Context**: Groww-inspired Mutual Fund Facts Assistant  
> **Approach**: Lightweight Retrieval-Augmented Generation (RAG)  
> **Guiding Principle**: *"Prioritizing verifiable accuracy and strict compliance over speculative intelligence."*

---

## 📌 1. Project Overview

The objective of this project is to build a **facts-only FAQ assistant** for mutual fund schemes, situated within the product context of **Groww** (one of India's leading investment and mutual fund platforms). 

Retail investors often struggle to find clear, verifiable, and authoritative answers to straightforward, factual questions about mutual funds (e.g., expense ratios, exit loads, lock-in terms, statement downloads). In financial domains, ungrounded AI models risk hallucinating figures or crossing the line into **unauthorized investment advice** (violating SEBI regulations).

This system solves this challenge by implementing an intelligent yet strictly bounded **RAG (Retrieval-Augmented Generation) assistant** that answers objective questions exclusively by retrieving verified data from official public regulatory and AMC sources. The assistant strictly abstains from subjective opinions, fund comparisons, and investment recommendations.

---

## 🎯 2. Core Objectives

1. **Facts-Only Grounded Answers**: Retrieve accurate, verifiable information solely from curated, authoritative documents (AMC factsheets, KIM, SID, AMFI, and SEBI).
2. **Deterministic Compliance & Refusal**: Politely refuse any question asking for advice, opinions, rankings, or performance predictions.
3. **Strict Response Formatting**: Enforce strict length limits (max 3 sentences), a single verified source URL citation, and a timestamp footer for freshness and transparency.
4. **Multi-Threaded User Experience**: Provide a clean, minimal, Groww-themed conversational UI supporting multiple independent chat threads.

---

## 👥 3. Target Audience & Personas

| Target Persona | Key Pain Point / Need | Value Delivered |
| :--- | :--- | :--- |
| **Retail Investors** | Overwhelmed by 50+ page SIDs/KIMs when searching for specific parameters (e.g., exit load periods, minimum SIP limits). | Instant, verifiable answers backed by a direct link to the official scheme document. |
| **First-Time / ELSS Investors** | Confused about statutory rules (e.g., Section 80C lock-in, tax deductions, capital gains statements). | Concise, factual clarification of regulatory terms without unsolicited sales pitches. |
| **Customer Support & Operations** | Flooded with repetitive, factual operational queries (e.g., how to download capital gains statement, cutoff times). | Consistent, automated deflection of L1 factual queries with 100% auditability. |

---

## 🔍 4. Scope of Work

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 END-TO-END SYSTEM SCOPE                                │
└────────────────────────────────────────────────────────────────────────────────────────┘
          │                                 │                                 │
          ▼                                 ▼                                 ▼
 1. CORPUS DEFINITION              2. RAG ASSISTANT ENGINE           3. GROWW-THEMED UI
 ├── 1 Chosen AMC (e.g., HDFC/ICICI)├── Semantic Retriever            ├── Welcome Screen
 ├── 3–5 Schemes (Multi-category)  ├── Query Intent Classifier       ├── 3 Prompt Starters
 ├── 15–25 Official URLs:          │   (Factual vs Advisory Refusal) ├── Multi-Chat Threads
 │   • SID, KIM, Factsheets        ├── Strict 3-Sentence Generator   └── Regulatory Disclaimers
 │   • AMFI/SEBI Guides            └── Citation & Timestamp Injector
 └── Zero Third-Party Blogs
```

### 4.1. Corpus Definition & Data Sourcing
- **Selected Asset Management Company (AMC)**: **HDFC Mutual Fund** (Reference Platform Context: Groww)
- **Selected Mutual Fund Schemes (Groww Reference Context)**:
  A curated set of 5 distinct schemes across diversified equity and commodity/FoF categories:

  | # | Scheme Name | Category | Groww Reference URL |
  | :--- | :--- | :--- | :--- |
  | 1 | **HDFC Mid-Cap Opportunities Fund** (Direct - Growth) | Equity: Mid Cap | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |
  | 2 | **HDFC Small Cap Fund** (Direct - Growth) | Equity: Small Cap | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
  | 3 | **HDFC Large and Mid Cap Fund** (Direct - Growth) | Equity: Large & Mid Cap | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
  | 4 | **HDFC Silver ETF Fund of Fund** (Direct - Growth) | Commodity: Silver FoF | https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth |
  | 5 | **HDFC Multi Cap Fund** (Direct - Growth) | Equity: Multi Cap | https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth |

- **Official Document Ingestion (15–25 Authoritative URLs)**:
  For each of the selected schemes above, ingest official statutory documents from HDFC AMC / AMFI / SEBI:
  - Scheme Information Documents (**SID**)
  - Key Information Memorandums (**KIM**)
  - Latest Monthly **Factsheets** (portfolio composition, expense ratios, AUM)
  - Official AMC FAQ and operational help articles
  - Regulatory portals: **AMFI** (Association of Mutual Funds in India) & **SEBI** (Securities and Exchange Board of India)
  - Official step-by-step guides for downloading account statements and capital gains reports.

### 4.2. Query Handling & Permitted Topics

The assistant is strictly calibrated to handle verifiable, objective data points:

| Permitted Query Category | Concrete Examples | Verification Source |
| :--- | :--- | :--- |
| **Costs & Fees** | "What is the expense ratio of the Flexi Cap Fund (Direct vs Regular)?" | Latest Monthly Factsheet |
| **Redemption Terms** | "What is the exit load if redeemed within 1 year?" | SID / KIM |
| **Investment Minimums** | "What is the minimum initial lump-sum and SIP amount?" | Scheme KIM / Factsheet |
| **Tax & Lock-in** | "What is the lock-in period for the ELSS scheme?" | SID / Income Tax Act guidelines |
| **Risk & Benchmarks** | "What is the scheme's Riskometer level and its benchmark index?" | Official Factsheet / SEBI Riskometer |
| **Operational Guidance** | "How can I download my annual capital gains statement or Consolidated Account Statement (CAS)?" | AMC / AMFI / CAMS / KFintech Official Guide |

### 4.3. Strict Response Contract
Every generated answer must conform to the following formatting specifications:
1. **Sentence Cap**: Maximum **3 sentences** in length.
2. **Single Authoritative Citation**: Exactly **one verified source URL** linking directly to the underlying official document.
3. **Mandatory Freshness Footer**:
   ```
   Last updated from sources: <YYYY-MM-DD>
   ```

### 4.4. Refusal Handling (Non-Factual / Advisory Queries)
The assistant must detect and refuse queries seeking subjective advice or market predictions.
- **Trigger Examples**:
  - *"Should I invest in HDFC Flexi Cap or Parag Parikh Flexi Cap?"*
  - *"Which fund will give me the highest returns this year?"*
  - *"Is this fund good for a 3-year horizon?"*
- **Refusal Response Protocol**:
  - Deliver a polite, neutral refusal acknowledging the inability to give opinions or advice.
  - Reiterate the assistant's strictly factual purpose.
  - Redirect the user to official educational material (e.g., AMFI's *Mutual Funds Sahi Hai* portal or SEBI Investor Education).

---

## 🚫 5. System Constraints & Regulatory Guardrails

```
                                  ┌─────────────────────────────┐
                                  │      SAFETY & COMPLIANCE    │
                                  └──────────────┬──────────────┘
                                                 │
         ┌───────────────────────────────┬───────┴───────────────────────┬───────────────────────────────┐
         ▼                               ▼                               ▼                               ▼
 🛡️ SOURCE INTEGRITY             🔒 ZERO PII / SECURITY          ⚖️ SEBI RIA COMPLIANCE          📜 TRANSPARENCY
 • Official AMC, AMFI, SEBI      • No PAN, Aadhaar               • No investment recommendations • Max 3 sentences
 • Strictly NO third-party       • No Folio/Account numbers      • No return projections / ROI   • Exactly 1 citation URL
   blogs, aggregators, or forums • No OTPs, Phone, or Email      • Factsheet-only links for perf • Timestamped footer
```

### 5.1. Data & Sourcing Constraints
- **Whitelisted Sources Only**: Strictly AMC official domains, AMFI India (`amfiindia.com`), and SEBI (`sebi.gov.in`).
- **Prohibited Sources**: Aggregator blogs (e.g., ValueResearch, Moneycontrol, ET Money), unofficial discussion forums (Reddit, Twitter), and third-party financial commentary websites.

### 5.2. Privacy, PII, and Information Security
The system must never prompt for, ingest, store, or log any Personally Identifiable Information (PII) or financial credentials:
- ❌ Permanent Account Number (PAN) or Aadhaar numbers
- ❌ Mutual Fund Folio numbers or Bank Account numbers
- ❌ One-Time Passwords (OTPs) or PINs
- ❌ User phone numbers or personal email addresses

### 5.3. Compliance with SEBI Investment Adviser Regulations
To prevent non-compliant advisory behavior:
- **No Recommendations**: Never suggest buying, holding, or switching funds.
- **No Relative Ranking**: Never declare one fund "better" or "superior" to another.
- **Performance Queries**: If a user asks about historical returns (e.g., 1-year, 3-year CAGR), the assistant must not calculate or interpret returns; it must provide the direct link to the latest official factsheet.

---

## 💻 6. User Interface Requirements (Groww Aesthetic)

The user interface must be clean, responsive, and aligned with Groww's modern aesthetic (rich typography, sleek dark/light theme, card containers):

1. **Header & Context**:
   - Prominent Disclaimer Tag: `Facts-only. No investment advice.`
   - Clear identification of the selected AMC and covered schemes.
2. **Starter Prompt Chips (3 Examples)**:
   - *"What is the expense ratio and exit load for HDFC Mid-Cap Opportunities Fund?"*
   - *"What is the minimum SIP amount for HDFC Silver ETF Fund of Fund?"*
   - *"How can I download my annual capital gains statement for HDFC Mutual Fund?"*
3. **Multi-Thread Chat Support**:
   - Sidebar allowing users to maintain multiple distinct conversation threads (e.g., *"HDFC ELSS Queries"*, *"Exit Load Questions"*).
   - Thread persistence during the user session.
4. **Answer Display Elements**:
   - Concise answer text (≤ 3 sentences).
   - Source pill/link formatted as a clickable citation.
   - Distinct metadata footer indicating data currency (`Last updated from sources: <date>`).

---

## 📦 7. Expected Deliverables

| Deliverable | Description | Key Contents |
| :--- | :--- | :--- |
| **1. Source Documents** | `Docs/problemstatement.txt` & `Docs/problemstatement.md` | Requirements baseline and structured reference documentation. |
| **2. Architecture Blueprint** | `Docs/architecture.md` | RAG pipeline architecture, chunking, embedding model, vector store, and refusal guardrails. |
| **3. Implementation Plan** | `Docs/implementation-plan.md` | Phased roadmap spanning data ingestion, RAG indexing, prompt engineering, and UI development. |
| **4. Ingestion & RAG Pipeline** | Python backend codebase | Document crawlers/loaders, chunking engine, vector database, and retrieval query pipeline. |
| **5. Frontend Application** | Web UI (Streamlit or Vite/React) | Minimal, elegant Groww-styled interface with multi-thread chat and persistent disclaimers. |
| **6. Comprehensive README** | `README.md` | Complete setup instructions, selected AMC/schemes, environment configurations, and known limitations. |

---

## ✅ 8. Success Criteria & Quality Metrics

- [ ] **Retrieval Accuracy**: Answers reflect 100% factual agreement with the ingested official documents.
- [ ] **Strict Adherence to Sentence Limits**: All responses contain between 1 and 3 sentences.
- [ ] **Citation Completeness**: 100% of answers provide exactly one verified citation link pointing to an official domain.
- [ ] **Freshness Traceability**: Every response contains the `Last updated from sources: <date>` footer.
- [ ] **Advisory Refusal Rate**: 100% refusal rate on subjective/comparative queries with polite redirection to investor education resources.
- [ ] **Clean, Intuitive UI**: Flawless switching between multiple conversation threads with a visible disclaimer banner.

---

> 🔗 **Source Reference**: Derived and expanded from [`Docs/problemstatement.txt`](file:///c:/Projects/Mutualfund_RAG/Docs/problemstatement.txt)
