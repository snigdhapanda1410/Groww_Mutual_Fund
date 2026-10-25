"""Guardrails and safety gate subsystem for Mutual Fund RAG."""

from src.state.models import QueryIntentResult
from src.guardrails.pii_redactor import detect_pii, redact_pii, get_pii_block_response
from src.guardrails.intent_classifier import (
    classify_intent,
    classify_intent_regex,
    classify_intent_llm,
    extract_scheme_id,
    extract_topic,
)
from src.guardrails.refusal_templates import (
    get_refusal_response,
    get_advisory_refusal,
    get_out_of_scope_refusal,
    get_pii_refusal,
    get_off_topic_refusal,
)


def run_guardrails(query: str) -> QueryIntentResult:
    """Execute the multi-tier safety pipeline on user query.
    
    1. Gate 1: PII Redaction Interceptor (blocks PAN, Aadhaar, Mobile, Email, Folio, Bank Account).
    2. Gate 2: Intent Classification Gate (Stage A: Regex Fast-Path, Stage B: LLM Fallback).
    
    Args:
        query: Raw user input text.
        
    Returns:
        Validated QueryIntentResult model ready for retrieval or immediate refusal.
    """
    # Gate 1: PII detection
    has_pii, pii_type = detect_pii(query)
    if has_pii:
        return QueryIntentResult(
            original_query=query,
            is_factual=False,
            is_advisory=False,
            has_pii=True,
            pii_type=pii_type,
            detected_scheme_id=extract_scheme_id(query),
            detected_topic=extract_topic(query),
            refusal_reason="pii_detected",
            classification_method="regex",
        )

    # Gate 2: Query intent classification
    return classify_intent(query)


__all__ = [
    "run_guardrails",
    "detect_pii",
    "redact_pii",
    "get_pii_block_response",
    "classify_intent",
    "classify_intent_regex",
    "classify_intent_llm",
    "extract_scheme_id",
    "extract_topic",
    "get_refusal_response",
    "get_advisory_refusal",
    "get_out_of_scope_refusal",
    "get_pii_refusal",
    "get_off_topic_refusal",
]
