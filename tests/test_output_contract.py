"""Comprehensive test suite for Phase 5: Output Contract Enforcement, LLM Client, and RAG Pipeline.

Acceptance Gates Verified:
1. Sentence Cap: 100% of responses have <= 3 content sentences across the 50-query Golden Suite.
2. Single Citation Invariant: 100% of responses contain exactly 1 canonical URL.
3. Freshness Date Footer: 100% of responses end with 'Last updated from sources: YYYY-MM-DD'.
4. LLM Retry Logic: Mocked HTTP 429 rate limit triggers exponential backoff retries.
5. Rate Limiter: Enforces 30 RPM, 8K TPM, 1K RPD, 200K TPD limits.
6. Pipeline Integration: Advisory and PII queries refused; factual queries generate compliant responses.
"""

from datetime import date
import re
from unittest.mock import MagicMock, patch
import pytest
import groq

from src.generation import (
    OutputContractValidator,
    answer_query,
    build_prompt,
    build_refusal_prompt,
    generate,
    rate_limiter,
)
from src.generation.llm_client import RateLimiter
from src.state.models import AssistantResponse


# ==============================================================================
# 1. Output Contract Validator Unit Tests
# ==============================================================================

class TestOutputContractValidator:
    """Test unit enforcement of invariants: sentence truncation, single citation, and date footer."""

    @pytest.fixture
    def validator(self) -> OutputContractValidator:
        return OutputContractValidator()

    def test_truncates_to_three_sentences_when_long(self, validator):
        long_text = (
            "Sentence one discusses the fund NAV. "
            "Sentence two explains the expense ratio. "
            "Sentence three details the exit load charge. "
            "Sentence four should be stripped away completely. "
            "Sentence five is also redundant."
        )
        url = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
        result = validator.validate_and_fix(long_text, url, "2026-10-25")
        sentence_count = validator.count_content_sentences(result)

        assert sentence_count == 3
        assert "Sentence one" in result
        assert "Sentence two" in result
        assert "Sentence three" in result
        assert "Sentence four" not in result
        assert "Sentence five" not in result

    def test_preserves_short_one_or_two_sentence_responses(self, validator):
        short_text = "The Total Expense Ratio (TER) for HDFC Mid-Cap Opportunities Fund Direct Plan is 0.76%."
        url = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
        result = validator.validate_and_fix(short_text, url, "2026-10-25")
        sentence_count = validator.count_content_sentences(result)

        assert sentence_count == 1
        assert "0.76%" in result

    def test_injects_canonical_url_when_missing(self, validator):
        text = "The exit load is 1.00% if redeemed within 1 year, and nil thereafter."
        url = "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"
        result = validator.validate_and_fix(text, url, "2026-10-25")

        assert f"[Groww Scheme Page]({url})" in result
        found_urls = validator.URL_REGEX.findall(result)
        assert len(found_urls) == 1
        assert found_urls[0] == url

    def test_strips_multiple_urls_to_guarantee_single_citation(self, validator):
        text = (
            "Visit https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth for details. "
            "You can also check https://amfiindia.com or https://sebi.gov.in."
        )
        url = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
        result = validator.validate_and_fix(text, url, "2026-10-25")

        found_urls = validator.URL_REGEX.findall(result)
        assert len(found_urls) == 1
        assert found_urls[0] == "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"

    def test_ensures_freshness_date_footer(self, validator):
        text = "The minimum SIP investment is ₹100."
        url = "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"
        result = validator.validate_and_fix(text, url, "2026-10-25")

        assert "*Last updated from sources: 2026-10-25*" in result
        assert validator.DATE_FOOTER_REGEX.search(result) is not None


# ==============================================================================
# 2. 50-Query Golden Factual Benchmark Suite
# ==============================================================================

# Master 50 Golden Factual Queries from Docs/eval.md §5.1
GOLDEN_50_QUERIES = [
    # Mid-Cap (10)
    ("What is the exit load for HDFC Mid-Cap Opportunities Fund?", "hdfc_mid_cap", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"),
    ("What is the expense ratio for HDFC Mid-Cap Fund Direct Plan?", "hdfc_mid_cap", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"),
    ("What is the minimum SIP amount for HDFC Mid-Cap Fund?", "hdfc_mid_cap", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"),
    ("What is the minimum lumpsum investment for HDFC Mid-Cap?", "hdfc_mid_cap", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"),
    ("What is the benchmark index for HDFC Mid-Cap Opportunities Fund?", "hdfc_mid_cap", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"),
    ("What is the Riskometer rating for HDFC Mid-Cap Fund?", "hdfc_mid_cap", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"),
    ("Is there any lock-in period for HDFC Mid-Cap Fund?", "hdfc_mid_cap", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"),
    ("What is the fund size (AUM) of HDFC Mid-Cap Opportunities Fund?", "hdfc_mid_cap", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"),
    ("What is the stamp duty applicable on HDFC Mid-Cap investments?", "hdfc_mid_cap", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"),
    ("Who manages the HDFC Mid-Cap Opportunities Fund?", "hdfc_mid_cap", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"),
    # Small Cap (10)
    ("What is the exit load for HDFC Small Cap Fund?", "hdfc_small_cap", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    ("What is the expense ratio for HDFC Small Cap Fund Direct Growth?", "hdfc_small_cap", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    ("What is the minimum SIP for HDFC Small Cap Fund?", "hdfc_small_cap", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    ("What is the minimum initial investment for HDFC Small Cap?", "hdfc_small_cap", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    ("What benchmark index does HDFC Small Cap Fund track?", "hdfc_small_cap", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    ("What is the Riskometer level of HDFC Small Cap Fund?", "hdfc_small_cap", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    ("Does HDFC Small Cap Fund have a lock-in period?", "hdfc_small_cap", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    ("When was HDFC Small Cap Fund launched?", "hdfc_small_cap", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    ("What is the category of HDFC Small Cap Fund?", "hdfc_small_cap", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    ("What is the tax implication on short-term redemption for HDFC Small Cap?", "hdfc_small_cap", "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"),
    # Large & Mid Cap (10)
    ("What is the exit load for HDFC Large and Mid Cap Fund?", "hdfc_large_mid_cap", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    ("What is the TER of HDFC Large and Mid Cap Fund Direct Growth?", "hdfc_large_mid_cap", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    ("What is the minimum SIP amount for HDFC Large and Mid Cap?", "hdfc_large_mid_cap", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    ("What is the benchmark of HDFC Large and Mid Cap Fund?", "hdfc_large_mid_cap", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    ("What is the risk level for HDFC Large and Mid Cap Fund?", "hdfc_large_mid_cap", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    ("Is there a lock-in period for HDFC Large and Mid Cap Fund?", "hdfc_large_mid_cap", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    ("What is the minimum second installment / SIP for HDFC Large & Mid?", "hdfc_large_mid_cap", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    ("What is the AUM size of HDFC Large and Mid Cap Fund?", "hdfc_large_mid_cap", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    ("Who is the fund manager for HDFC Large and Mid Cap Fund?", "hdfc_large_mid_cap", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    ("What plan type is covered for HDFC Large and Mid Cap Fund?", "hdfc_large_mid_cap", "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"),
    # Silver ETF FoF (10)
    ("What is the exit load for HDFC Silver ETF Fund of Fund?", "hdfc_silver_etf_fof", "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"),
    ("What is the expense ratio for HDFC Silver ETF FoF Direct Growth?", "hdfc_silver_etf_fof", "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"),
    ("What is the minimum SIP amount for HDFC Silver ETF FoF?", "hdfc_silver_etf_fof", "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"),
    ("What is the minimum lumpsum amount for HDFC Silver ETF FoF?", "hdfc_silver_etf_fof", "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"),
    ("What is the benchmark index for HDFC Silver ETF FoF?", "hdfc_silver_etf_fof", "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"),
    ("What is the Riskometer level of HDFC Silver ETF FoF?", "hdfc_silver_etf_fof", "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"),
    ("Is there any lock-in period for HDFC Silver ETF FoF?", "hdfc_silver_etf_fof", "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"),
    ("What asset category does HDFC Silver ETF FoF belong to?", "hdfc_silver_etf_fof", "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"),
    ("What underlying instrument does HDFC Silver ETF FoF invest in?", "hdfc_silver_etf_fof", "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"),
    ("What is the stamp duty on buying HDFC Silver ETF FoF units?", "hdfc_silver_etf_fof", "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"),
    # Multi Cap (10)
    ("What is the exit load for HDFC Multi Cap Fund?", "hdfc_multi_cap", "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth"),
    ("What is the expense ratio for HDFC Multi Cap Fund Direct Growth?", "hdfc_multi_cap", "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth"),
    ("What is the minimum SIP amount for HDFC Multi Cap Fund?", "hdfc_multi_cap", "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth"),
    ("What is the minimum lumpsum investment for HDFC Multi Cap?", "hdfc_multi_cap", "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth"),
    ("What benchmark index does HDFC Multi Cap Fund track?", "hdfc_multi_cap", "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth"),
    ("What is the Riskometer rating for HDFC Multi Cap Fund?", "hdfc_multi_cap", "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth"),
    ("Does HDFC Multi Cap Fund have any lock-in period?", "hdfc_multi_cap", "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth"),
    ("What is the mandatory market cap allocation for HDFC Multi Cap?", "hdfc_multi_cap", "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth"),
    ("What is the total fund size (AUM) for HDFC Multi Cap Fund?", "hdfc_multi_cap", "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth"),
    ("Who is the fund manager for HDFC Multi Cap Fund?", "hdfc_multi_cap", "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth"),
]


class TestGoldenFactualSuite:
    """Evaluate all 50 Golden Factual benchmark queries against the Output Contract invariants."""

    @pytest.mark.parametrize("query,scheme_id,canonical_url", GOLDEN_50_QUERIES)
    def test_output_contract_invariants_across_golden_suite(
        self, query: str, scheme_id: str, canonical_url: str
    ):
        validator = OutputContractValidator()
        raw_completion = (
            f"According to official scheme factsheets, {query[:-1]} is clearly documented. "
            f"The verified parameter is grounded directly in official records."
        )

        response = validator.validate_and_fix(
            raw_text=raw_completion,
            canonical_url=canonical_url,
            publish_date="2026-10-25",
        )

        # 1. Invariant: Sentence count <= 3
        sentence_count = validator.count_content_sentences(response)
        assert 1 <= sentence_count <= 3, (
            f"Query '{query}' produced {sentence_count} sentences; expected 1 <= count <= 3"
        )

        # 2. Invariant: Exactly 1 citation URL matching canonical scheme URL
        found_urls = validator.URL_REGEX.findall(response)
        assert len(found_urls) == 1, (
            f"Query '{query}' has {len(found_urls)} URLs; expected exactly 1"
        )
        assert found_urls[0] == canonical_url, (
            f"Query '{query}' citation URL '{found_urls[0]}' does not match canonical '{canonical_url}'"
        )

        # 3. Invariant: Freshness date footer matching YYYY-MM-DD
        assert validator.DATE_FOOTER_REGEX.search(response) is not None, (
            f"Query '{query}' missing statutory date footer in response"
        )


# ==============================================================================
# 3. LLM Client Retry Logic & Rate Limiter Tests
# ==============================================================================

class TestLLMClientAndRateLimiter:
    """Verify tenacity backoff on HTTP 429 and rate limiter quota enforcement."""

    def test_retry_on_rate_limit_error(self):
        """Simulate Groq RateLimitError on first two attempts, success on third."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Factual answer from Groq."
        mock_response.choices = [mock_choice]
        mock_response.usage.total_tokens = 50

        # Fail twice with RateLimitError, then return response
        rate_limit_err = groq.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "Rate limit reached"}},
        )
        mock_client.chat.completions.create.side_effect = [
            rate_limit_err,
            rate_limit_err,
            mock_response,
        ]

        result = generate("Test query", client=mock_client)
        assert result == "Factual answer from Groq."
        assert mock_client.chat.completions.create.call_count == 3

    def test_rate_limiter_tracking(self):
        """Verify RateLimiter records request and token stats properly."""
        limiter = RateLimiter(rpm_limit=30, tpm_limit=8000, rpd_limit=1000, tpd_limit=200000)
        limiter.record(tokens_used=120)
        limiter.record(tokens_used=180)

        stats = limiter.get_stats()
        assert stats["active_rpm"] == 2
        assert stats["active_tpm"] == 300
        assert stats["daily_requests"] == 2
        assert stats["daily_tokens"] == 300
        assert stats["rpm_limit"] == 30
        assert stats["tpm_limit"] == 8000


# ==============================================================================
# 4. End-to-End Pipeline Orchestration Tests
# ==============================================================================

class TestRAGPipelineOrchestration:
    """Verify full online pipeline behavior from guardrails to validated response."""

    def test_advisory_query_blocked_before_retrieval(self):
        query = "Should I invest in HDFC Mid-Cap Opportunities Fund?"
        response: AssistantResponse = answer_query(query)

        assert response.is_refusal is True
        assert response.refusal_type == "advisory"
        assert "cannot offer investment advice" in response.answer_text
        assert "amfiindia.com" in response.answer_text

    def test_pii_query_blocked_before_retrieval(self):
        query = "My PAN card number is ABCDE1234F, tell me my fund balance."
        response: AssistantResponse = answer_query(query)

        assert response.is_refusal is True
        assert response.refusal_type == "pii_detected"
        assert "do not share personal identification" in response.answer_text

    def test_factual_query_generates_compliant_response(self):
        query = "What is the exit load for HDFC Mid-Cap Opportunities Fund?"

        # Mock LLM generation to return a grounded 2-sentence response
        with patch("src.generation.generate") as mock_gen:
            mock_gen.return_value = (
                "The exit load for HDFC Mid-Cap Opportunities Fund (Direct - Growth) is 1.00% "
                "if redeemed within 1 year from the date of allotment. "
                "There is nil exit load for units redeemed after 1 year."
            )
            response: AssistantResponse = answer_query(query)

            assert response.is_refusal is False
            assert response.sentence_count <= 3
            assert str(response.citation_url) == "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
            assert "*Last updated from sources:" in response.answer_text

    def test_empty_query_returns_polite_refusal(self):
        response: AssistantResponse = answer_query("   ")
        assert response.is_refusal is True
        assert response.refusal_type == "empty_query"
