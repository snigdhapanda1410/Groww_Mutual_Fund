"""Phase 1 Acceptance Gate Tests: Setup, Configuration, Models, and Logger."""

import json
from pathlib import Path
import pytest
from datetime import date, datetime

from src.config import config, Settings
from src.state.models import (
    DocumentChunk,
    QueryIntentResult,
    RetrievedContext,
    AssistantResponse,
    Thread,
    Message,
    ThreadSummary,
)
from src.utils.logger import get_logger, JSONFormatter


def test_config_loads_cleanly():
    """Verify that configuration loads without error with default or env settings."""
    assert config is not None
    assert isinstance(config.app_title, str)
    assert "Groww" in config.app_title
    assert config.max_output_sentences == 3
    assert config.enforce_single_citation is True
    assert config.similarity_threshold == 0.65
    assert config.groq_model in ("openai/gpt-oss-120b", "llama-3.3-70b-versatile")


def test_directory_and_init_stubs_exist():
    """Verify that all required package __init__.py files exist."""
    required_inits = [
        Path("src/__init__.py"),
        Path("src/ingestion/__init__.py"),
        Path("src/guardrails/__init__.py"),
        Path("src/retrieval/__init__.py"),
        Path("src/generation/__init__.py"),
        Path("src/state/__init__.py"),
        Path("src/utils/__init__.py"),
        Path("ui/__init__.py"),
        Path("tests/__init__.py"),
    ]
    for init_file in required_inits:
        assert init_file.exists(), f"Missing required file: {init_file}"


def test_sources_manifest_contains_strictly_five_groww_urls():
    """Verify that sources_manifest.json contains strictly the 5 canonical Groww URLs."""
    manifest_path = Path("data/sources_manifest.json")
    assert manifest_path.exists(), "data/sources_manifest.json must exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("total_sources") == 5
    assert len(manifest.get("sources", [])) == 5

    expected_urls = {
        "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
        "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth",
    }
    extracted_urls = {s["url"] for s in manifest["sources"]}
    assert extracted_urls == expected_urls, f"Manifest URLs mismatch: {extracted_urls}"

    expected_schemes = {
        "hdfc_mid_cap",
        "hdfc_small_cap",
        "hdfc_large_mid_cap",
        "hdfc_silver_etf_fof",
        "hdfc_multi_cap",
    }
    extracted_schemes = {s["scheme_id"] for s in manifest["sources"]}
    assert extracted_schemes == expected_schemes


def test_pydantic_models_validation():
    """Verify Pydantic models instantiate and validate fields correctly."""
    # 1. DocumentChunk
    chunk = DocumentChunk(
        scheme_id="hdfc_mid_cap",
        scheme_name="HDFC Mid-Cap Opportunities Fund (Direct - Growth)",
        category="Equity: Mid Cap",
        source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        publish_date=date(2026, 9, 30),
        section="Expense Ratio & Exit Load",
        content="| Parameter | Details |\n|---|---|\n| Expense Ratio | 0.72% |",
        content_type="table",
    )
    assert chunk.scheme_id == "hdfc_mid_cap"
    assert str(chunk.source_url).startswith("https://groww.in/")

    # 2. AssistantResponse Output Contract
    resp = AssistantResponse(
        answer_text="The expense ratio for HDFC Mid-Cap Opportunities Fund Direct Plan is 0.72%. Exit load is 1% if redeemed within 1 year.",
        sentence_count=2,
        citation_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        last_updated_date=date(2026, 9, 30),
        thread_id="test-123",
    )
    assert resp.sentence_count == 2
    formatted = resp.formatted_output()
    assert "**Source**:" in formatted
    assert "*Last updated from sources: 2026-09-30*" in formatted

    # 3. Sentence Count > 3 raises error
    with pytest.raises(ValueError):
        AssistantResponse(
            answer_text="Sentence one. Sentence two. Sentence three. Sentence four.",
            sentence_count=4,
            citation_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            last_updated_date=date(2026, 9, 30),
            thread_id="test-123",
        )

    # 4. Thread & Message
    thread = Thread(title="HDFC Mid-Cap Questions")
    msg = Message(
        role="user",
        content="What is the exit load?",
    )
    thread.messages.append(msg)
    assert len(thread.messages) == 1
    assert thread.messages[0].role == "user"


def test_logger_outputs_valid_json(capsys):
    """Verify that get_logger logs structured JSON to stdout/stderr."""
    test_logger = get_logger("test_module")
    test_logger.info("Phase 1 verified")

    captured = capsys.readouterr()
    log_output = captured.err or captured.out
    assert log_output, "Logger produced no output"

    parsed = json.loads(log_output.strip().split("\n")[-1])
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Phase 1 verified"
    assert "timestamp" in parsed


def test_gitignore_contains_env():
    """Verify that .env is excluded from git tracking."""
    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists(), ".gitignore must exist"
    content = gitignore_path.read_text(encoding="utf-8")
    assert ".env" in content
