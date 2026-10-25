# 🚀 Deployment Plan: Mutual Fund FAQ Assistant (Railway + Vercel)

> The complete, production-grade deployment plan is documented in [`Docs/deployment-plan.md`](file:///c:/Projects/Mutualfund_RAG/Docs/deployment-plan.md).

### Quick Links
- 📘 **Full Deployment Document**: [`Docs/deployment-plan.md`](file:///c:/Projects/Mutualfund_RAG/Docs/deployment-plan.md)
- 🏗️ **Architecture Document**: [`Docs/architecture.md`](file:///c:/Projects/Mutualfund_RAG/Docs/architecture.md)
- 📋 **Implementation Plan**: [`Docs/implementation-plan.md`](file:///c:/Projects/Mutualfund_RAG/Docs/implementation-plan.md)
- ⚙️ **Daily Ingestion Workflow**: [`.github/workflows/daily_ingestion.yml`](file:///c:/Projects/Mutualfund_RAG/.github/workflows/daily_ingestion.yml)

---

### Overview at a Glance

| Component | Target Platform | Runtime / Tech | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend API** | [Railway.app](https://railway.app/) | Python 3.11 / FastAPI / Docker | Houses ChromaDB (30 chunks on 5GB Persistent Volume), SentenceTransformers embeddings, PII & Advisory Guardrails, Groq LLM client (`openai/gpt-oss-120b`), and disk-backed session manager. |
| **Frontend Web UI** | [Vercel](https://vercel.com/) | Edge CDN / Next.js or Static SPA | Delivers the Groww Obsidian Emerald dark mode interface with sub-50ms TTFB, SEBI disclaimer banner, 5 scheme cards, quick prompt chips, and a reverse proxy `/api/*` rewrite to Railway. |
| **Data Ingestion** | GitHub Actions | POSIX Cron `30 4 * * *` (Daily 10:00 AM IST) | Automatically crawls the 5 Groww URLs, extracts tables, re-indexes ChromaDB, and triggers the Railway deploy hook. |
