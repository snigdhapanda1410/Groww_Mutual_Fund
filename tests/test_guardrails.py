"""Comprehensive unit and acceptance tests for Phase 3: Guardrails & Safety Gates."""

import pytest
from datetime import date

from src.guardrails.pii_redactor import detect_pii, redact_pii, get_pii_block_response
from src.guardrails.intent_classifier import (
    classify_intent,
    classify_intent_regex,
    extract_scheme_id,
    extract_topic,
)
from src.guardrails.refusal_templates import (
    get_advisory_refusal,
    get_out_of_scope_refusal,
    get_pii_refusal,
    get_off_topic_refusal,
    get_refusal_response,
)
from src.guardrails import run_guardrails


# ==============================================================================
# 1. PII REDACTION INTERCEPTOR TESTS (15 PII Queries + 10 Clean Queries)
# ==============================================================================

@pytest.mark.parametrize(
    "query, expected_type",
    [
        # PAN (5 letters, 4 digits, 1 letter)
        ("My PAN is ABCDE1234F, what is my exit load?", "PAN"),
        ("Here is my pan card number: BKZPR4589K for KYC", "PAN"),
        ("Update folio with pan abcde9876z please", "PAN"),
        
        # Aadhaar (12 digits with or without spaces/hyphens)
        ("My Aadhaar is 1234 5678 9012, check my investment", "Aadhaar"),
        ("Aadhaar: 9876-5432-1098 linked to my account", "Aadhaar"),
        ("Verify identity using 234567890123 aadhaar", "Aadhaar"),
        
        # Mobile Numbers (Indian 10 digits starting with 6-9)
        ("Call me on 9876543210 regarding mid cap returns", "Mobile"),
        ("My phone number is +91 9123456789", "Mobile"),
        ("Send details to +91-8765432109", "Mobile"),
        ("Contact mobile: 7987654321", "Mobile"),
        
        # Email Addresses
        ("Send the statement to investor.hdfc@gmail.com", "Email"),
        ("My email is user.name+mf@corporate.in", "Email"),
        
        # Mutual Fund Folio Numbers
        ("My folio is 12345678, what is my balance?", "Folio"),
        ("Folio: 98765432105 please tell me my NAV", "Folio"),
        ("Check account no: 543216789 for HDFC fund", "Folio"),
        
        # Bank Account Numbers
        ("My bank account is 987654321012345 for payout", "BankAccount"),
    ],
)
def test_pii_detection_blocks_sensitive_queries(query, expected_type):
    """Verify detect_pii flags all forms of sensitive personal financial identifiers."""
    has_pii, pii_type = detect_pii(query)
    assert has_pii is True, f"Failed to detect PII in: '{query}'"
    assert pii_type == expected_type, f"Expected {expected_type}, got {pii_type}"


@pytest.mark.parametrize(
    "clean_query",
    [
        "What is the expense ratio of HDFC Mid-Cap fund?",
        "What is the exit load for HDFC Small Cap?",
        "Minimum SIP amount for HDFC Silver ETF FoF",
        "Who is the fund manager of HDFC Multi Cap?",
        "What is the benchmark index for HDFC Large and Mid Cap?",
        "What is the NAV on 23-Oct-2026?",
        "Tell me the lock-in period for mid cap",
        "What are the top 10 holdings in small cap fund?",
        "Explain stamp duty on mutual funds in India",
        "Does HDFC Silver ETF direct plan have an exit load?",
    ],
)
def test_pii_detection_passes_clean_queries(clean_query):
    """Verify clean factual queries pass through PII gate without false positives."""
    has_pii, pii_type = detect_pii(clean_query)
    assert has_pii is False, f"False positive PII detected in: '{clean_query}' ({pii_type})"
    assert pii_type is None


def test_pii_redaction_sanitization():
    """Verify redact_pii masks sensitive values for audit logging."""
    raw = "Investor PAN ABCDE1234F with mobile 9876543210 and email test@amc.com"
    sanitized = redact_pii(raw)
    assert "ABCDE1234F" not in sanitized
    assert "9876543210" not in sanitized
    assert "test@amc.com" not in sanitized
    assert "[REDACTED_PAN]" in sanitized
    assert "[REDACTED_MOBILE]" in sanitized
    assert "[REDACTED_EMAIL]" in sanitized


# ==============================================================================
# 2. ADVISORY QUERY DETECTION TESTS (20 Obvious Advisory Queries)
# ==============================================================================

@pytest.mark.parametrize(
    "advisory_query",
    [
        "Should I invest in HDFC Mid Cap fund right now?",
        "Which fund is best for high returns?",
        "Which is better between HDFC Mid Cap and HDFC Small Cap?",
        "Can you recommend a good mutual fund for 5 years?",
        "Suggest a fund to invest 10000 rupees monthly",
        "What is the expected return of HDFC Multi Cap fund?",
        "Will HDFC Small Cap fund grow faster than Large Cap?",
        "Compare HDFC Mid Cap vs HDFC Small Cap fund",
        "Which is safer between mid cap and silver etf?",
        "Is HDFC Silver ETF good for long term?",
        "Should I buy or sell HDFC Large and Mid Cap units?",
        "Should I switch from small cap to multi cap fund?",
        "Would you advise investing in equity funds now?",
        "How much profit will I get if I invest 1 lakh?",
        "Is this fund good for my retirement portfolio?",
        "Can I expect 20% CAGR from HDFC Small Cap?",
        "What is your suggestion on the best HDFC scheme?",
        "Will the NAV of silver ETF rise next month?",
        "Should I redeem my mutual fund before 1 year?",
        "Which scheme is more profitable for short term?",
    ],
)
def test_advisory_regex_flags_investment_advice(advisory_query):
    """Verify Stage A regex fast-path detects advisory and speculative queries."""
    is_adv, reason = classify_intent_regex(advisory_query)
    assert is_adv is True, f"Failed to flag advisory query: '{advisory_query}'"
    assert reason == "advisory"


# ==============================================================================
# 3. FACTUAL QUERY PASS-THROUGH TESTS (20 Authoritative Factual Queries)
# ==============================================================================

@pytest.mark.parametrize(
    "factual_query, expected_scheme, expected_topic",
    [
        ("What is the expense ratio of HDFC Mid Cap?", "hdfc_mid_cap", "expense_ratio"),
        ("What is the exit load for HDFC Small Cap?", "hdfc_small_cap", "exit_load"),
        ("What is the minimum SIP amount in HDFC Silver ETF?", "hdfc_silver_etf_fof", "minimum_investment"),
        ("Who is the fund manager of HDFC Multi Cap?", "hdfc_multi_cap", "fund_manager"),
        ("What is the benchmark index for HDFC Large and Mid Cap?", "hdfc_large_mid_cap", "benchmark"),
        ("What is the NAV of HDFC Mid Cap Opportunities fund?", "hdfc_mid_cap", "nav"),
        ("What are the top 10 holdings in HDFC Small Cap?", "hdfc_small_cap", "holdings"),
        ("What is the lock-in period for HDFC Mid Cap fund?", "hdfc_mid_cap", "lock_in"),
        ("What is the stamp duty on HDFC Multi Cap purchase?", "hdfc_multi_cap", "capital_gains"),
        ("What is the fund size AUM of HDFC Large Cap?", "hdfc_large_mid_cap", "nav"),
        ("What is the minimum lumpsum in HDFC Silver ETF?", "hdfc_silver_etf_fof", "minimum_investment"),
        ("Tell me the exit load period for HDFC Silver ETF FoF", "hdfc_silver_etf_fof", "exit_load"),
        ("Who manages HDFC Small Cap fund?", "hdfc_small_cap", "fund_manager"),
        ("What percentage of HDFC Multi Cap is invested in large cap stocks?", "hdfc_multi_cap", "holdings"),
        ("What is the TER of HDFC Mid Cap Direct Plan?", "hdfc_mid_cap", "expense_ratio"),
        ("What is the capital gains tax for HDFC Large and Mid Cap?", "hdfc_large_mid_cap", "capital_gains"),
        ("What benchmark does HDFC Small Cap track?", "hdfc_small_cap", "benchmark"),
        ("What is the minimum additional investment for HDFC Mid Cap?", "hdfc_mid_cap", "minimum_investment"),
        ("Does HDFC Large and Mid Cap have a lock-in period?", "hdfc_large_mid_cap", "lock_in"),
        ("What are the top holdings of HDFC Silver ETF?", "hdfc_silver_etf_fof", "holdings"),
    ],
)
def test_factual_queries_pass_and_extract_entities(factual_query, expected_scheme, expected_topic):
    """Verify factual queries pass through safety gate with extracted scheme and topic entities."""
    intent = classify_intent(factual_query)
    assert intent.is_factual is True, f"Factual query incorrectly flagged as advisory: '{factual_query}'"
    assert intent.is_advisory is False
    assert intent.has_pii is False
    assert intent.refusal_reason is None
    assert intent.detected_scheme_id == expected_scheme, f"Expected {expected_scheme}, got {intent.detected_scheme_id}"
    assert intent.detected_topic == expected_topic, f"Expected {expected_topic}, got {intent.detected_topic}"


# ==============================================================================
# 4. REFUSAL TEMPLATES COMPLIANCE TESTS
# ==============================================================================

def test_refusal_templates_compliance_links_and_dates():
    """Verify all refusal templates meet regulatory compliance and statutory date formatting."""
    today_str = date.today().strftime("%Y-%m-%d")

    # Advisory refusal
    adv_text = get_advisory_refusal()
    assert "https://www.amfiindia.com/investor-corner/knowledge-center" in adv_text
    assert "https://www.sebi.gov.in/investor.html" in adv_text
    assert f"*Last updated from sources: {today_str}*" in adv_text
    assert "I cannot offer investment advice" in adv_text

    # Out of scope refusal
    oos_text = get_out_of_scope_refusal()
    assert "https://groww.in/mutual-funds" in oos_text
    assert f"*Last updated from sources: {today_str}*" in oos_text
    assert "Mid-Cap Opportunities" in oos_text
    assert "Small Cap" in oos_text

    # PII refusal
    pii_text = get_pii_refusal()
    assert "PAN" in pii_text
    assert "Aadhaar" in pii_text
    assert "folio numbers" in pii_text

    # Dispatcher tests
    assert get_refusal_response("advisory") == adv_text
    assert get_refusal_response("pii_detected") == pii_text
    assert get_refusal_response("out_of_scope") == oos_text


# ==============================================================================
# 5. GUARDRAIL ORCHESTRATOR INTEGRATION TESTS
# ==============================================================================

def test_guardrails_orchestrator_pii_precedence():
    """Verify Gate 1 (PII) takes precedence over intent classification."""
    # An advisory query containing a PAN should be blocked for PII first
    query = "Should I invest in HDFC Mid Cap? My PAN is ABCDE1234F"
    res = run_guardrails(query)
    assert res.has_pii is True
    assert res.pii_type == "PAN"
    assert res.refusal_reason == "pii_detected"
    assert res.is_factual is False


def test_guardrails_orchestrator_advisory_block():
    """Verify Gate 2 blocks pure advisory query without PII."""
    query = "Which mutual fund should I invest in for the best returns?"
    res = run_guardrails(query)
    assert res.has_pii is False
    assert res.is_advisory is True
    assert res.is_factual is False
    assert res.refusal_reason == "advisory"


def test_guardrails_orchestrator_factual_allow():
    """Verify clean factual query cleanly reaches retrieval stage."""
    query = "What is the expense ratio of HDFC Small Cap fund?"
    res = run_guardrails(query)
    assert res.has_pii is False
    assert res.is_advisory is False
    assert res.is_factual is True
    assert res.detected_scheme_id == "hdfc_small_cap"
    assert res.detected_topic == "expense_ratio"
    assert res.refusal_reason is None
