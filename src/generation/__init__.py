"""Generation subsystem for LLM prompting, invocation, and output contract validation."""

from datetime import date, datetime
from typing import Optional

from src.config import config
from src.guardrails import run_guardrails
from src.guardrails.refusal_templates import (
    get_advisory_refusal,
    get_off_topic_refusal,
    get_out_of_scope_refusal,
    get_pii_refusal,
    get_refusal_response,
)
from src.retrieval import (
    assemble_context,
    extract_entities,
    rerank_chunks,
    retrieve_chunks,
)
from src.generation.llm_client import generate, get_groq_client, set_groq_client, rate_limiter
from src.generation.output_formatter import OutputContractValidator
from src.generation.prompt_templates import build_prompt, build_refusal_prompt
from src.state.models import AssistantResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "answer_query",
    "build_prompt",
    "build_refusal_prompt",
    "generate",
    "get_groq_client",
    "set_groq_client",
    "rate_limiter",
    "OutputContractValidator",
]


def answer_query(query: str, thread_id: str = "") -> AssistantResponse:
    """End-to-end facts-only RAG pipeline:
    
    1. Safety Gates: Intercept PII and advisory intent.
    2. Entity Extraction: Map query to canonical scheme_id and topic.
    3. Filtered Vector Retrieval: Fetch top-k chunks with confidence gating.
    4. Optional Secondary Reranking: Reciprocal Rank Fusion if enabled.
    5. Context Assembly: Structure context chunks with statutory metadata.
    6. LLM Generation: Call Groq API with deterministic settings.
    7. Output Contract Validation: Enforce <=3 sentences, 1 citation, and date footer.
    
    Args:
        query: User input query text.
        thread_id: Optional conversation session identifier.
        
    Returns:
        Certified AssistantResponse model.
    """
    clean_query = query.strip()
    if not clean_query:
        return AssistantResponse(
            answer_text="Please enter a question regarding one of the 5 supported HDFC mutual fund schemes.",
            sentence_count=1,
            citation_url="https://groww.in/mutual-funds",
            last_updated_date=date.today(),
            is_refusal=True,
            thread_id=thread_id,
            refusal_type="empty_query",
        )

    # --------------------------------------------------------------------------
    # Step 1: Guardrails & Safety Gates
    # --------------------------------------------------------------------------
    intent = run_guardrails(clean_query)

    if intent.has_pii:
        logger.info(f"PII detected in query; blocking before retrieval/LLM.")
        return AssistantResponse(
            answer_text=get_pii_refusal(),
            sentence_count=2,
            citation_url="https://groww.in/mutual-funds",
            last_updated_date=date.today(),
            is_refusal=True,
            thread_id=thread_id,
            refusal_type="pii_detected",
        )

    if intent.is_advisory:
        logger.info(f"Advisory intent detected in query; generating refusal.")
        return AssistantResponse(
            answer_text=get_advisory_refusal(),
            sentence_count=3,
            citation_url="https://www.amfiindia.com/investor-corner/knowledge-center",
            last_updated_date=date.today(),
            is_refusal=True,
            thread_id=thread_id,
            refusal_type="advisory",
        )

    # --------------------------------------------------------------------------
    # Step 2: Entity Extraction
    # --------------------------------------------------------------------------
    scheme_id, topic = extract_entities(clean_query)

    # --------------------------------------------------------------------------
    # Step 3: Filtered Vector Retrieval
    # --------------------------------------------------------------------------
    chunks = retrieve_chunks(
        query=clean_query,
        scheme_id=scheme_id,
        top_k=config.retrieval_top_k,
    )

    if not chunks:
        logger.info(f"Zero context chunks retrieved for query '{clean_query[:50]}...'. Triggering fallback.")
        if scheme_id:
            # Query targeted a covered scheme, but parameter was not found in page
            no_context_msg = (
                "The provided official documents do not contain this information. "
                "Please consult groww.in for further scheme updates.\n\n"
                "**Source**: [https://groww.in/mutual-funds](https://groww.in/mutual-funds)\n\n"
                f"*Last updated from sources: {date.today().strftime('%Y-%m-%d')}*"
            )
            return AssistantResponse(
                answer_text=no_context_msg,
                sentence_count=2,
                citation_url="https://groww.in/mutual-funds",
                last_updated_date=date.today(),
                is_refusal=True,
                thread_id=thread_id,
                refusal_type="no_context",
            )
        else:
            # Scheme was outside coverage or completely off-topic
            return AssistantResponse(
                answer_text=get_out_of_scope_refusal(),
                sentence_count=3,
                citation_url="https://groww.in/mutual-funds",
                last_updated_date=date.today(),
                is_refusal=True,
                thread_id=thread_id,
                refusal_type="out_of_scope",
            )

    # --------------------------------------------------------------------------
    # Step 4: Optional Reranking
    # --------------------------------------------------------------------------
    chunks = rerank_chunks(query=clean_query, chunks=chunks)

    # --------------------------------------------------------------------------
    # Step 5: Context Assembly
    # --------------------------------------------------------------------------
    context_text, canonical_url, publish_date_str = assemble_context(chunks)

    try:
        publish_date = datetime.strptime(publish_date_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        publish_date = date.today()

    # --------------------------------------------------------------------------
    # Step 6: LLM Generation
    # --------------------------------------------------------------------------
    prompt = build_prompt(
        context=context_text,
        query=clean_query,
        source_url=canonical_url,
    )
    try:
        raw_llm_response = generate(prompt)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}; returning safe context fallback.")
        raw_llm_response = (
            "The provided official documents do not contain this information. "
            "Please consult groww.in for latest scheme data."
        )

    # --------------------------------------------------------------------------
    # Step 7: Output Contract Validation & Enforcement
    # --------------------------------------------------------------------------
    validator = OutputContractValidator()
    clean_response = validator.validate_and_fix(
        raw_text=raw_llm_response,
        canonical_url=canonical_url,
        publish_date=publish_date.strftime("%Y-%m-%d"),
    )

    sentence_count = validator.count_content_sentences(clean_response)
    # Guarantee sentence count invariant <= 3 for Pydantic validator
    sentence_count = min(3, max(1, sentence_count))

    return AssistantResponse(
        answer_text=clean_response,
        sentence_count=sentence_count,
        citation_url=canonical_url,
        last_updated_date=publish_date,
        is_refusal=False,
        thread_id=thread_id,
    )
