"""Unit and integration tests for FastAPI REST endpoints and deployment configurations."""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from src.api.main import app


client = TestClient(app)


class TestAPIEndpoints:
    """Validate FastAPI REST endpoints."""

    def test_root_endpoint(self):
        """GET / must return 200 with service metadata and documentation links."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["documentation"] == "/docs"
        assert data["health_check"] == "/health"

    def test_health_check_endpoint(self):
        """GET /health must return 200 with ChromaDB collection metrics and model info."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "mutualfund-rag-backend"
        assert data["chunks_indexed"] == 30
        assert "all-MiniLM-L6-v2" in data["embedding_model"]
        assert "openai/gpt-oss-120b" in data["llm_model"]

    def test_list_covered_schemes_endpoint(self):
        """GET /api/schemes must return strictly the 5 canonical Groww HDFC mutual funds."""
        response = client.get("/api/schemes")
        assert response.status_code == 200
        schemes = response.json()
        assert len(schemes) == 5

        expected_ids = {
            "hdfc_mid_cap",
            "hdfc_small_cap",
            "hdfc_large_mid_cap",
            "hdfc_silver_etf_fof",
            "hdfc_multi_cap",
        }
        found_ids = {s["scheme_id"] for s in schemes}
        assert found_ids == expected_ids

        for s in schemes:
            assert s["url"].startswith("https://groww.in/mutual-funds/hdfc-")
            assert s["expense_ratio"] != "N/A"
            assert s["exit_load"] != "N/A"
            assert s["nav"] != "N/A"

    def test_chat_factual_query(self):
        """POST /api/chat with a factual query returns certified <=3 sentence response with citation."""
        payload = {
            "query": "What is the exit load of HDFC Small Cap Fund?",
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "thread_id" in data
        assert data["query"] == payload["query"]
        assert data["is_refusal"] is False
        assert data["citation_url"] == "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"
        assert len(data["content"]) > 10
        assert "execution_time_ms" in data

    def test_chat_advisory_query_refusal(self):
        """POST /api/chat with advisory query triggers SEBI compliance refusal with AMFI link."""
        payload = {
            "query": "Should I invest in HDFC Mid-Cap Opportunities Fund?",
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["is_refusal"] is True
        assert data["refusal_type"] == "advisory"
        assert "investment advice" in data["content"].lower()
        assert "amfiindia.com" in data["content"].lower()

    def test_chat_pii_query_blocked(self):
        """POST /api/chat with Indian financial PII is intercepted before RAG/LLM calls."""
        payload = {
            "query": "My PAN card is ABCDE1234F, show my HDFC fund details",
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["is_refusal"] is True
        assert data["refusal_type"] == "pii_detected"
        assert "personal identification details" in data["content"].lower()

    def test_session_lifecycle(self):
        """Create, fetch, and delete conversation threads through REST endpoints."""
        # 1. Create session
        create_res = client.post("/api/sessions", params={"title": "Deployment Test Thread"})
        assert create_res.status_code == 201
        created = create_res.json()
        thread_id = created["thread_id"]
        assert created["title"] == "Deployment Test Thread"

        # 2. Query in this session
        chat_res = client.post("/api/chat", json={"query": "What is HDFC Multi Cap NAV?", "thread_id": thread_id})
        assert chat_res.status_code == 200

        # 3. List sessions
        list_res = client.get("/api/sessions")
        assert list_res.status_code == 200
        threads = list_res.json()
        assert any(t["thread_id"] == thread_id for t in threads)

        # 4. Get session history
        history_res = client.get(f"/api/sessions/{thread_id}")
        assert history_res.status_code == 200
        history = history_res.json()
        assert len(history["messages"]) >= 2

        # 5. Delete session
        del_res = client.delete(f"/api/sessions/{thread_id}")
        assert del_res.status_code == 200

        # 6. Verify 404 after deletion
        missing_res = client.get(f"/api/sessions/{thread_id}")
        assert missing_res.status_code == 404


class TestDeploymentConfigurations:
    """Verify production deployment configuration files."""

    def test_dockerfile_configuration(self):
        """Dockerfile must specify python:3.11-slim, model caching, non-root user, entrypoint, and start command."""
        dockerfile = Path("Dockerfile")
        assert dockerfile.exists(), "Missing Dockerfile"
        content = dockerfile.read_text(encoding="utf-8")

        assert "FROM python:3.11-slim" in content
        assert "sentence-transformers/all-MiniLM-L6-v2" in content
        assert "useradd" in content
        assert "USER appuser" in content
        assert "entrypoint.sh" in content
        assert "src.api.main" in content

    def test_railway_json_configuration(self):
        """railway.json must configure Dockerfile builder and health check."""
        railway_file = Path("railway.json")
        assert railway_file.exists(), "Missing railway.json"
        data = json.loads(railway_file.read_text(encoding="utf-8"))

        assert data["build"]["builder"] == "DOCKERFILE"
        assert data["deploy"]["healthcheckPath"] == "/health"

    def test_procfile_configuration(self):
        """Procfile must contain web process command using python -m src.api.main."""
        procfile = Path("Procfile")
        assert procfile.exists(), "Missing Procfile"
        content = procfile.read_text(encoding="utf-8")
        assert "src.api.main" in content

    def test_entrypoint_script_exists(self):
        """scripts/entrypoint.sh and scripts/entrypoint.py must exist."""
        entrypoint_sh = Path("scripts/entrypoint.sh")
        entrypoint_py = Path("scripts/entrypoint.py")
        wrapper_py = Path("scripts/uvicorn_wrapper.py")

        assert entrypoint_sh.exists(), "Missing scripts/entrypoint.sh"
        assert entrypoint_py.exists(), "Missing scripts/entrypoint.py"
        assert wrapper_py.exists(), "Missing scripts/uvicorn_wrapper.py"

    def test_entrypoint_argument_sanitization(self):
        """scripts/entrypoint.py sanitize_args must replace literal $PORT and ${PORT}."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("entrypoint_mod", "scripts/entrypoint.py")
        entrypoint_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entrypoint_mod)

        # Test array format: ['uvicorn', 'src.api.main:app', '--port', '$PORT']
        res1 = entrypoint_mod.sanitize_args(["uvicorn", "src.api.main:app", "--port", "$PORT"], "9000")
        assert res1 == ["uvicorn", "src.api.main:app", "--port", "9000"]

        # Test single string format: ['uvicorn src.api.main:app --port $PORT --workers 2']
        res2 = entrypoint_mod.sanitize_args(["uvicorn src.api.main:app --port $PORT --workers 2"], "9000")
        assert res2 == ["uvicorn", "src.api.main:app", "--port", "9000", "--workers", "2"]

        # Test --port=${PORT} format
        res3 = entrypoint_mod.sanitize_args(["uvicorn", "src.api.main:app", "--port=${PORT}"], "7500")
        assert res3 == ["uvicorn", "src.api.main:app", "--port=7500"]

    def test_railway_and_nixpacks_toml(self):
        """railway.toml and nixpacks.toml must specify python -m src.api.main."""
        railway_toml = Path("railway.toml")
        nixpacks_toml = Path("nixpacks.toml")
        assert railway_toml.exists(), "Missing railway.toml"
        assert nixpacks_toml.exists(), "Missing nixpacks.toml"

        assert "python -m src.api.main" in railway_toml.read_text(encoding="utf-8")
        assert "python -m src.api.main" in nixpacks_toml.read_text(encoding="utf-8")

    def test_vercel_json_configuration(self):
        """vercel.json must configure reverse proxy rewrites to Railway and security headers."""
        vercel_file = Path("vercel.json")
        assert vercel_file.exists(), "Missing vercel.json"
        data = json.loads(vercel_file.read_text(encoding="utf-8"))

        assert "rewrites" in data
        rewrites = data["rewrites"]
        assert any(r["source"] == "/api/:path*" for r in rewrites)
        assert any(r["source"] == "/health" for r in rewrites)

        assert "headers" in data

    def test_frontend_web_app_artifacts(self):
        """Root and frontend directory must contain index.html, app.js, and styles.css."""
        assert Path("index.html").exists(), "Missing root index.html"
        assert Path("app.js").exists(), "Missing root app.js"
        assert Path("styles.css").exists(), "Missing root styles.css"

        frontend_dir = Path("frontend")
        assert (frontend_dir / "index.html").exists(), "Missing frontend/index.html"
        assert (frontend_dir / "app.js").exists(), "Missing frontend/app.js"
        assert (frontend_dir / "styles.css").exists(), "Missing frontend/styles.css"

        html_content = Path("index.html").read_text(encoding="utf-8")
        assert "SEBI Compliance" in html_content
        assert "Covered HDFC Direct Schemes" in html_content
