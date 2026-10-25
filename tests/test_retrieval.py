"""Unit and integration tests for Phase 4: Retrieval & Context Assembly Pipeline.

Acceptance Gates Verified:
1. Scheme entity extraction (5 schemes + 8 topic categories).
2. Metadata-filtered query (100% scheme isolation in ChromaDB).
3. Retrieval latency benchmark (< 500ms warm query latency).
4. Low-similarity rejection (out-of-domain queries return empty list).
5. Context block format verification (=== CONTEXT N === headers, canonical URL, date).
6. Reranker module (pass-through vs RRF ranking).
"""

from datetime import date
import time
import pytest

from src.retrieval.entity_extractor import (
    SCHEME_ALIASES,
    TOPIC_KEYWORDS,
    extract_entities,
    extract_scheme_id,
    extract_topic,
)
from src.retrieval.retriever import (
    build_metadata_filter,
    retrieve_chunks,
)
from src.retrieval.reranker import rerank_chunks
from src.retrieval.context_assembler import assemble_context
from src.state.models import DocumentChunk, RetrievedContext


# ==============================================================================
# 1. Entity Extraction Tests (Scheme ID and Topic)
# ==============================================================================

class TestEntityExtractor:
    """Evaluate accuracy of scheme alias matching and topic extraction."""

    @pytest.mark.parametrize(
        "query,expected_scheme_id",
        [
            # HDFC Mid-Cap
            ("What is the expense ratio of HDFC Mid-Cap?", "hdfc_mid_cap"),
            ("Tell me about mid cap opportunities fund", "hdfc_mid_cap"),
            ("What is the NAV of hdfc mid cap?", "hdfc_mid_cap"),
            ("Is midcap direct growth available?", "hdfc_mid_cap"),
            # HDFC Small Cap
            ("What is the exit load of HDFC Small Cap?", "hdfc_small_cap"),
            ("small cap direct plan details", "hdfc_small_cap"),
            ("hdfc small fund minimum sip", "hdfc_small_cap"),
            ("smallcap lock in period", "hdfc_small_cap"),
            # HDFC Large & Mid Cap (must not collide with mid cap)
            ("What is the expense ratio of HDFC Large and Mid Cap?", "hdfc_large_mid_cap"),
            ("large & mid cap fund details", "hdfc_large_mid_cap"),
            ("hdfc large cap exit load", "hdfc_large_mid_cap"),
            ("large and mid performance", "hdfc_large_mid_cap"),
            # HDFC Silver ETF FoF
            ("What is the minimum sip for HDFC Silver ETF FoF?", "hdfc_silver_etf_fof"),
            ("silver fund exit load", "hdfc_silver_etf_fof"),
            ("silver etf investment amount", "hdfc_silver_etf_fof"),
            ("silver fof direct growth details", "hdfc_silver_etf_fof"),
            # HDFC Multi Cap
            ("What is the portfolio of HDFC Multi Cap?", "hdfc_multi_cap"),
            ("multicap fund expense ratio", "hdfc_multi_cap"),
            ("hdfc multi fund holdings", "hdfc_multi_cap"),
            ("multi-cap direct growth exit load", "hdfc_multi_cap"),
        ],
    )
    def test_entity_extractor_scheme_ids(self, query: str, expected_scheme_id: str):
        """Verify 100% precision for canonical scheme ID resolution across all 5 schemes."""
        extracted = extract_scheme_id(query)
        assert extracted == expected_scheme_id, (
            f"Query '{query}' resolved to '{extracted}', expected '{expected_scheme_id}'"
        )

    @pytest.mark.parametrize(
        "query,expected_topic",
        [
            ("What is the exit load of the fund?", "exit_load"),
            ("Is there any redemption charge or penalty?", "exit_load"),
            ("What is the total expense ratio (TER)?", "expense_ratio"),
            ("What are the annual management fees?", "expense_ratio"),
            ("What is the minimum SIP amount?", "minimum_investment"),
            ("minimum additional investment required", "minimum_investment"),
            ("What is the lock-in period for this fund?", "lock_in"),
            ("What is the benchmark index for HDFC Mid Cap?", "benchmark"),
            ("What is the riskometer rating of the fund?", "riskometer"),
            ("How can I download my consolidated account statement (CAS)?", "cas"),
            ("What are the capital gains tax implications under 80C?", "capital_gains"),
            ("Who is the fund manager managing this portfolio?", "fund_manager"),
            ("What are the top 10 portfolio holdings?", "holdings"),
            ("What is the latest NAV and fund size?", "nav"),
        ],
    )
    def test_entity_extractor_topics(self, query: str, expected_topic: str):
        """Verify topic extraction across all financial parameter categories."""
        extracted = extract_topic(query)
        assert extracted == expected_topic, (
            f"Query '{query}' resolved to topic '{extracted}', expected '{expected_topic}'"
        )

    def test_entity_extractor_combined(self):
        """Verify extract_entities returns both scheme and topic simultaneously."""
        query = "What is the exit load of HDFC Mid-Cap Opportunities Fund?"
        scheme_id, topic = extract_entities(query)
        assert scheme_id == "hdfc_mid_cap"
        assert topic == "exit_load"

    def test_entity_extractor_unrelated_query(self):
        """Verify unrelated queries yield None for both entities."""
        query = "What is the capital of France?"
        scheme_id, topic = extract_entities(query)
        assert scheme_id is None
        assert topic is None

    def test_entity_extractor_empty_query(self):
        """Verify empty and whitespace strings return None cleanly."""
        assert extract_scheme_id("") is None
        assert extract_topic("") is None
        assert extract_entities("") == (None, None)


# ==============================================================================
# 2. Metadata Filter Builder Tests
# ==============================================================================

class TestMetadataFilterBuilder:
    """Test ChromaDB 'where' clause construction."""

    def test_build_filter_scheme_only(self):
        filt = build_metadata_filter(scheme_id="hdfc_mid_cap")
        assert filt == {"scheme_id": {"$eq": "hdfc_mid_cap"}}

    def test_build_filter_composite(self):
        filt = build_metadata_filter(
            scheme_id="hdfc_mid_cap",
            section="Expense Ratio & Exit Load",
        )
        assert filt == {
            "$and": [
                {"scheme_id": {"$eq": "hdfc_mid_cap"}},
                {"section": {"$eq": "Expense Ratio & Exit Load"}},
            ]
        }

    def test_build_filter_empty(self):
        assert build_metadata_filter() is None


# ==============================================================================
# 3. Vector Retriever Integration Tests (ChromaDB)
# ==============================================================================

class TestVectorRetriever:
    """Verify live ChromaDB retrieval: scheme isolation, latency, outlier rejection."""

    def test_scheme_isolation(self):
        """Ensure 100% scheme isolation: querying hdfc_mid_cap returns 0 small_cap chunks."""
        chunks = retrieve_chunks(
            query="What is the expense ratio and exit load?",
            scheme_id="hdfc_mid_cap",
            top_k=3,
        )
        assert len(chunks) > 0, "Expected at least 1 chunk for valid mid-cap query"
        for rc in chunks:
            assert rc.chunk.scheme_id == "hdfc_mid_cap", (
                f"Contamination detected! Expected 'hdfc_mid_cap' but got '{rc.chunk.scheme_id}'"
            )
            assert "small" not in rc.chunk.scheme_id.lower()

    def test_retrieval_latency_benchmark(self):
        """Benchmark warm retrieval latency: must be < 500ms per query."""
        # Warmup query to ensure models/caches are hot
        _ = retrieve_chunks(
            query="What is the exit load?",
            scheme_id="hdfc_mid_cap",
            top_k=3,
        )

        test_queries = [
            ("What is the expense ratio?", "hdfc_mid_cap"),
            ("What is the minimum sip amount?", "hdfc_small_cap"),
            ("What is the lock-in period?", "hdfc_large_mid_cap"),
            ("What is the benchmark index?", "hdfc_silver_etf_fof"),
            ("Who are the fund managers?", "hdfc_multi_cap"),
        ]

        latencies = []
        for q, sid in test_queries:
            t0 = time.perf_counter()
            results = retrieve_chunks(query=q, scheme_id=sid, top_k=3)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)

        max_latency = max(latencies)
        median_latency = sorted(latencies)[len(latencies) // 2]

        assert max_latency < 500.0, (
            f"Retrieval latency failed: max {max_latency:.1f}ms exceeds 500ms gate"
        )
        assert median_latency < 200.0, (
            f"Median latency {median_latency:.1f}ms exceeds 200ms benchmark target"
        )

    def test_low_confidence_rejection(self):
        """Verify out-of-domain queries (e.g. cricket, weather) return empty list."""
        out_of_domain_queries = [
            "Who won the cricket match yesterday in Melbourne?",
            "What is the weather forecast for Mumbai tomorrow?",
            "How do I bake a chocolate cake at home?",
        ]

        for query in out_of_domain_queries:
            results = retrieve_chunks(query=query, top_k=3)
            assert results == [], (
                f"Expected 0 chunks for out-of-domain query '{query}', but got {len(results)}"
            )

    def test_empty_query_returns_empty_list(self):
        """Verify empty query string returns empty list immediately without error."""
        assert retrieve_chunks("") == []
        assert retrieve_chunks("   ") == []


# ==============================================================================
# 4. Context Assembler Tests
# ==============================================================================

class TestContextAssembler:
    """Verify structured prompt context block construction."""

    @pytest.fixture
    def sample_chunks(self) -> list[RetrievedContext]:
        c1 = DocumentChunk(
            chunk_id="chunk_001",
            scheme_id="hdfc_mid_cap",
            scheme_name="HDFC Mid-Cap Opportunities Fund (Direct - Growth)",
            category="Equity: Mid Cap",
            doc_type="GrowwPage",
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            publish_date=date(2026, 10, 25),
            section="Expense Ratio & Exit Load",
            content="| Expense Ratio | 0.76% |\n| Exit Load | 1.0% |",
            content_type="table",
        )
        c2 = DocumentChunk(
            chunk_id="chunk_002",
            scheme_id="hdfc_mid_cap",
            scheme_name="HDFC Mid-Cap Opportunities Fund (Direct - Growth)",
            category="Equity: Mid Cap",
            doc_type="GrowwPage",
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            publish_date=date(2026, 10, 25),
            section="Minimum Investment & Lock-in",
            content="| Minimum SIP | ₹100 |\n| Lock-in | Nil |",
            content_type="table",
        )
        return [
            RetrievedContext(chunk=c1, similarity_score=0.85, rank=1),
            RetrievedContext(chunk=c2, similarity_score=0.75, rank=2),
        ]

    def test_assemble_context_structure(self, sample_chunks):
        context_text, canonical_url, pub_date = assemble_context(sample_chunks)

        # Header structure checks
        assert "=== CONTEXT 1 (Source: GrowwPage | Scheme: HDFC Mid-Cap Opportunities Fund (Direct - Growth) | Date: 2026-10-25) ===" in context_text
        assert "=== CONTEXT 2 (Source: GrowwPage | Scheme: HDFC Mid-Cap Opportunities Fund (Direct - Growth) | Date: 2026-10-25) ===" in context_text

        # Content inclusion
        assert "| Expense Ratio | 0.76% |" in context_text
        assert "| Minimum SIP | ₹100 |" in context_text

        # Statutory citation attributes
        assert canonical_url == "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
        assert pub_date == "2026-10-25"

    def test_assemble_context_empty(self):
        context_text, canonical_url, pub_date = assemble_context([])
        assert context_text == ""
        assert canonical_url == ""
        assert pub_date == ""


# ==============================================================================
# 5. Reranker Tests
# ==============================================================================

class TestReranker:
    """Verify reranker in pass-through and RRF modes."""

    @pytest.fixture
    def sample_ranked_chunks(self) -> list[RetrievedContext]:
        c1 = DocumentChunk(
            chunk_id="chunk_overview",
            scheme_id="hdfc_mid_cap",
            scheme_name="HDFC Mid-Cap Opportunities Fund",
            category="Equity: Mid Cap",
            doc_type="GrowwPage",
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            publish_date=date(2026, 10, 25),
            section="Fund Overview & Benchmark",
            content="The fund aims to generate long-term capital appreciation from a portfolio of mid-cap stocks.",
            content_type="text",
        )
        c2 = DocumentChunk(
            chunk_id="chunk_expense",
            scheme_id="hdfc_mid_cap",
            scheme_name="HDFC Mid-Cap Opportunities Fund",
            category="Equity: Mid Cap",
            doc_type="GrowwPage",
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            publish_date=date(2026, 10, 25),
            section="Expense Ratio & Exit Load",
            content="The Total Expense Ratio (TER) is 0.76% and exit load is 1% if redeemed within 1 year.",
            content_type="table",
        )
        return [
            RetrievedContext(chunk=c1, similarity_score=0.82, rank=1),
            RetrievedContext(chunk=c2, similarity_score=0.79, rank=2),
        ]

    def test_reranker_pass_through(self, sample_ranked_chunks):
        """When use_reranker=False, input order is strictly preserved."""
        reranked = rerank_chunks(
            query="What is the exit load?",
            chunks=sample_ranked_chunks,
            use_reranker=False,
        )
        assert [r.chunk.chunk_id for r in reranked] == ["chunk_overview", "chunk_expense"]
        assert [r.rank for r in reranked] == [1, 2]

    def test_reranker_rrf_boosts_keyword_overlap(self, sample_ranked_chunks):
        """When use_reranker=True, chunk with high query keyword overlap gets boosted."""
        reranked = rerank_chunks(
            query="What is the exit load and expense ratio TER?",
            chunks=sample_ranked_chunks,
            use_reranker=True,
        )
        # chunk_expense contains 'exit', 'load', 'expense', 'ratio', 'ter' - should be promoted to Rank 1
        assert reranked[0].chunk.chunk_id == "chunk_expense"
        assert reranked[0].rank == 1
        assert reranked[1].chunk.chunk_id == "chunk_overview"
        assert reranked[1].rank == 2

    def test_reranker_empty_list(self):
        assert rerank_chunks("query", []) == []
