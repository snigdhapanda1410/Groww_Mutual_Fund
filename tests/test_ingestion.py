"""Automated tests for Phase 2: Crawler (2.1) and HTML & Table Parser (2.2)."""

import json
from pathlib import Path
import pytest

from src.ingestion.crawler import compute_sha256, is_update_needed, crawl_all
from src.ingestion.html_parser import parse_groww_page, _format_markdown_table


def test_crawler_manifest_reading():
    """Verify manifest exists and defines strictly 5 canonical Groww sources."""
    manifest_path = Path("data/sources_manifest.json")
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("total_sources") == 5
    assert len(manifest.get("sources", [])) == 5


def test_crawler_hashing(tmp_path):
    """Verify compute_sha256 computes a valid 64-character hex digest."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("HDFC Mutual Fund RAG Assistant", encoding="utf-8")
    h = compute_sha256(test_file)
    assert isinstance(h, str)
    assert len(h) == 64


def test_crawler_idempotency(tmp_path):
    """Verify is_update_needed returns False when hash matches stored manifest hash."""
    test_file = tmp_path / "page.html"
    test_file.write_text("<html>Sample Content</html>", encoding="utf-8")
    h = compute_sha256(test_file)

    manifest_entry = {"sha256": h}
    assert is_update_needed(manifest_entry, test_file) is False

    # Modifying content triggers update needed
    test_file.write_text("<html>Modified Content</html>", encoding="utf-8")
    assert is_update_needed(manifest_entry, test_file) is True


def test_all_five_groww_snapshots_exist():
    """Verify all 5 scheme HTML snapshots were fetched and stored on disk."""
    schemes = [
        "hdfc_mid_cap",
        "hdfc_small_cap",
        "hdfc_large_mid_cap",
        "hdfc_silver_etf_fof",
        "hdfc_multi_cap",
    ]
    for s in schemes:
        snapshot_path = Path(f"data/raw/{s}/groww_page.html")
        assert snapshot_path.exists(), f"Snapshot missing for {s}"
        assert snapshot_path.stat().st_size > 50000, f"Snapshot unexpectedly small for {s}"


def test_markdown_table_formatter():
    """Verify markdown table helper outputs valid GFM tables with pipe delimiters."""
    headers = ["Parameter", "Value"]
    rows = [["Expense Ratio", "0.74%"], ["Exit Load", "1% within 1 yr"]]
    table = _format_markdown_table(headers, rows)
    assert "Parameter" in table and "Value" in table
    assert "| ---" in table
    assert "Expense Ratio" in table and "0.74%" in table
    assert table.startswith("| ")
    assert table.count("\n") >= 2


def test_html_parser_extracts_structured_blocks_for_all_schemes():
    """Verify parse_groww_page parses all 5 schemes into required table & text blocks."""
    with open("data/sources_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for entry in manifest["sources"]:
        sid = entry["scheme_id"]
        sname = entry["scheme_name"]
        url = entry["url"]
        path = Path(entry["download_path"])

        blocks = parse_groww_page(path, sid, sname, url)
        assert len(blocks) >= 5, f"Expected at least 5 blocks for {sid}, got {len(blocks)}"

        sections = {b["section"] for b in blocks}
        assert "Expense Ratio & Exit Load" in sections
        assert "Minimum Investment & Lock-in" in sections
        assert "Fund Overview & Benchmark" in sections

        for b in blocks:
            assert b["scheme_id"] == sid
            assert b["scheme_name"] == sname
            assert b["source_url"] == url
            assert "publish_date" in b
            assert len(b["content"].strip()) > 0


def test_html_parser_grounded_financial_values():
    """Verify specific financial parameters extracted from Groww match reality."""
    # 1. HDFC Silver ETF FoF: Exit load is 15 days, TER is 0.21%
    silver_path = Path("data/raw/hdfc_silver_etf_fof/groww_page.html")
    silver_blocks = parse_groww_page(
        silver_path,
        "hdfc_silver_etf_fof",
        "HDFC Silver ETF Fund of Fund (Direct - Growth)",
        "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
    )
    exp_block = next(b for b in silver_blocks if b["section"] == "Expense Ratio & Exit Load")
    assert "0.21%" in exp_block["content"]
    assert "15 days" in exp_block["content"]

    # 2. HDFC Mid-Cap: Minimum SIP is ₹100, Benchmark is NIFTY Midcap 150
    mid_path = Path("data/raw/hdfc_mid_cap/groww_page.html")
    mid_blocks = parse_groww_page(
        mid_path,
        "hdfc_mid_cap",
        "HDFC Mid-Cap Opportunities Fund (Direct - Growth)",
        "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    )
    min_block = next(b for b in mid_blocks if b["section"] == "Minimum Investment & Lock-in")
    assert "₹100" in min_block["content"]

    overview_block = next(b for b in mid_blocks if b["section"] == "Fund Overview & Benchmark")
    assert "NIFTY Midcap 150" in overview_block["content"]
    assert "Direct Plan - Growth Option" in overview_block["content"]


def test_chunker_generates_atomic_chunks_with_breadcrumbs():
    """Verify chunk_document produces atomic DocumentChunks with semantic headers."""
    from src.ingestion.chunker import chunk_document

    sample_blocks = [
        {
            "scheme_id": "hdfc_mid_cap",
            "scheme_name": "HDFC Mid-Cap Opportunities Fund (Direct - Growth)",
            "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "section": "Expense Ratio & Exit Load",
            "content": "| Parameter | Value |\n|---|---|\n| Expense Ratio | 0.72% |\n| Exit Load | 1.00% |",
            "content_type": "table",
            "publish_date": "2026-10-25",
        }
    ]

    chunks = chunk_document(sample_blocks, category="Equity: Mid Cap")
    assert len(chunks) == 1
    c = chunks[0]
    assert c.chunk_id == "hdfc_mid_cap_expense_ratio_exit_load_0"
    assert c.scheme_id == "hdfc_mid_cap"
    assert "### Scheme: HDFC Mid-Cap Opportunities Fund" in c.content
    assert "| Expense Ratio | 0.72% |" in c.content
    assert c.content_type == "table"
    assert c.publish_date.isoformat() == "2026-10-25"
    assert c.token_count is not None and c.token_count > 0


def test_chromadb_acceptance_gate_collection_count_and_schemes():
    """Phase 2 Acceptance Gate: Verify ChromaDB contains exactly 30 chunks across all 5 schemes."""
    from src.ingestion.indexer import get_chroma_client, get_or_create_collection

    client = get_chroma_client()
    col = get_or_create_collection(client)
    assert col.count() == 30, f"Expected 30 chunks in collection, found {col.count()}"

    schemes = [
        "hdfc_mid_cap",
        "hdfc_small_cap",
        "hdfc_large_mid_cap",
        "hdfc_silver_etf_fof",
        "hdfc_multi_cap",
    ]
    for s in schemes:
        res = col.get(where={"scheme_id": s})
        assert len(res["ids"]) == 6, f"Expected 6 chunks for {s}, found {len(res['ids'])}"


def test_chromadb_scheme_isolation_and_table_preservation():
    """Phase 2 Acceptance Gate: Verify scheme isolation filter and Markdown table preservation."""
    from src.ingestion.indexer import get_chroma_client, get_or_create_collection, get_embedding_function

    client = get_chroma_client()
    ef = get_embedding_function()
    col = get_or_create_collection(client, embedding_function=ef)

    # Query strictly for hdfc_silver_etf_fof
    res = col.query(
        query_texts=["What is the expense ratio and exit load for Silver ETF?"],
        n_results=1,
        where={"scheme_id": "hdfc_silver_etf_fof"},
    )
    assert len(res["ids"][0]) == 1
    meta = res["metadatas"][0][0]
    doc = res["documents"][0][0]

    assert meta["scheme_id"] == "hdfc_silver_etf_fof"
    assert "groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth" in meta["source_url"]
    assert meta["publish_date"].startswith("2026")
    # Verify table formatting is intact
    assert "|" in doc and "---" in doc


def test_chromadb_distance_metric_is_cosine():
    """Phase 2 Acceptance Gate: Verify HNSW distance space is configured as cosine."""
    from src.ingestion.indexer import get_chroma_client, get_or_create_collection

    client = get_chroma_client()
    col = get_or_create_collection(client)
    assert col.metadata.get("hnsw:space") == "cosine"

