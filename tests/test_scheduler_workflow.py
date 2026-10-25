"""Unit tests for Phase 7: Automated Daily Ingestion Scheduler & GitHub Actions Workflow."""

from pathlib import Path
import yaml
import pytest

from src.ingestion.crawler import read_manifest
from src.ingestion.indexer import index_all


WORKFLOW_PATH = Path(".github/workflows/daily_ingestion.yml")


class TestGitHubActionsWorkflow:
    """Validate structure, triggers, and configuration of daily_ingestion.yml."""

    def test_workflow_file_exists(self):
        """Workflow file must exist at .github/workflows/daily_ingestion.yml."""
        assert WORKFLOW_PATH.exists(), f"Workflow file missing at {WORKFLOW_PATH}"
        assert WORKFLOW_PATH.is_file()

    def test_workflow_yaml_validity(self):
        """Workflow file must be valid YAML with core root elements."""
        content = WORKFLOW_PATH.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)

        assert isinstance(parsed, dict)
        assert "name" in parsed
        assert ("on" in parsed or True in parsed)
        assert "concurrency" in parsed
        assert "jobs" in parsed

    def test_workflow_cron_timing_10am_ist(self):
        """Workflow cron schedule must be '30 4 * * *' (04:30 UTC = 10:00 AM IST)."""
        content = WORKFLOW_PATH.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)

        on_section = parsed.get("on") or parsed.get(True) or {}
        schedule_section = on_section.get("schedule", [])
        assert len(schedule_section) >= 1, "Missing schedule section in workflow triggers"

        cron_entry = schedule_section[0].get("cron")
        assert cron_entry == "30 4 * * *", (
            f"Expected cron '30 4 * * *' (10:00 AM IST = 04:30 UTC), got '{cron_entry}'"
        )

    def test_workflow_dispatch_configuration(self):
        """Workflow must support workflow_dispatch with force_crawl and rebuild_index."""
        content = WORKFLOW_PATH.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)

        on_section = parsed.get("on") or parsed.get(True) or {}
        assert "workflow_dispatch" in on_section, "Missing workflow_dispatch trigger"

        inputs = on_section["workflow_dispatch"].get("inputs", {})
        assert "force_crawl" in inputs, "Missing force_crawl input in workflow_dispatch"
        assert inputs["force_crawl"].get("type") == "boolean"
        assert inputs["force_crawl"].get("default") is True

        assert "rebuild_index" in inputs, "Missing rebuild_index input in workflow_dispatch"
        assert inputs["rebuild_index"].get("type") == "boolean"
        assert inputs["rebuild_index"].get("default") is True

    def test_workflow_concurrency_control(self):
        """Concurrency must ensure cancel-in-progress is false to avoid DB lock collision."""
        content = WORKFLOW_PATH.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)

        concurrency = parsed.get("concurrency", {})
        assert concurrency.get("group") == "daily-ingestion"
        assert concurrency.get("cancel-in-progress") is False

    def test_workflow_job_pipeline_steps(self):
        """Ingestion job must contain all 5 lifecycle steps: scrape, normalize/chunk/embed/store, test, commit, artifact."""
        content = WORKFLOW_PATH.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)

        job = parsed.get("jobs", {}).get("daily-ingestion", {})
        assert job.get("runs-on") == "ubuntu-latest"

        steps = job.get("steps", [])
        step_names = [s.get("name", "") for s in steps]
        step_runs = [s.get("run", "") for s in steps if "run" in s]

        # 1. Setup Python
        assert any("Python" in name for name in step_names), "Missing Python setup step"

        # 2. Dependency install
        assert any("pip install" in run for run in step_runs), "Missing pip dependency installation step"

        # 3. Scraping execution
        assert any("src.ingestion.crawler" in run for run in step_runs), "Missing crawler scraping step"

        # 4. Ingestion / ChromaDB indexing
        assert any("src.ingestion.indexer" in run for run in step_runs), "Missing indexer step"

        # 5. Verification tests
        assert any("pytest" in run for run in step_runs), "Missing pytest verification step"

        # 6. Commit manifest
        assert any("stefanzweifel/git-auto-commit-action" in s.get("uses", "") for s in steps), (
            "Missing manifest git auto-commit step"
        )

        # 7. Upload ChromaDB artifact
        assert any("actions/upload-artifact" in s.get("uses", "") for s in steps), (
            "Missing upload-artifact step"
        )

    def test_workflow_artifact_paths(self):
        """Artifact step must preserve chromadb, raw data snapshots, and sources_manifest."""
        content = WORKFLOW_PATH.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)

        steps = parsed.get("jobs", {}).get("daily-ingestion", {}).get("steps", [])
        artifact_step = next(
            (s for s in steps if "actions/upload-artifact" in s.get("uses", "")),
            None,
        )
        assert artifact_step is not None, "Missing upload-artifact step"

        with_block = artifact_step.get("with", {})
        paths = with_block.get("path", "")
        assert "data/chromadb/" in paths
        assert "data/raw/" in paths
        assert "data/sources_manifest.json" in paths


class TestIngestionPipelineAutomation:
    """Validate CLI flags and automated execution of the daily ingestion pipeline."""

    def test_crawler_manifest_integrity(self):
        """Manifest must contain strictly 5 canonical Groww schemes with URLs and hashes."""
        manifest = read_manifest()
        sources = manifest.get("sources", [])
        assert len(sources) == 5, f"Expected 5 schemes in manifest, got {len(sources)}"

        expected_ids = {
            "hdfc_mid_cap",
            "hdfc_small_cap",
            "hdfc_large_mid_cap",
            "hdfc_silver_etf_fof",
            "hdfc_multi_cap",
        }
        found_ids = {s["scheme_id"] for s in sources}
        assert found_ids == expected_ids

        for entry in sources:
            assert entry["url"].startswith("https://groww.in/mutual-funds/hdfc-")
            assert "sha256" in entry
            assert len(entry["sha256"]) == 64

    def test_indexer_returns_success_and_thirty_chunks(self):
        """Running index_all(rebuild=False) verifies the 30 atomic chunks in ChromaDB."""
        summary = index_all(rebuild=False)
        assert summary["status"] == "success"
        assert summary["total_sources"] == 5
        assert summary["collection_total_count"] == 30
        for scheme_id, count in summary["schemes"].items():
            assert count == 6, f"Expected 6 chunks for {scheme_id}, got {count}"
