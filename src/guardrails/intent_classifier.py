"""Query Intent Classifier providing fast regex fast-path and LLM fallback."""

import os
import re
from typing import Optional, Tuple

from src.config import config
from src.state.models import QueryIntentResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Canonical scheme aliases mapping to the 5 supported Groww schemes
SCHEME_ALIASES = {
    "hdfc_large_mid_cap": [
        "hdfc large and mid cap", "hdfc large & mid cap", "hdfc large and mid", "hdfc large & mid",
        "large and mid cap", "large and mid", "large & mid cap", "large & mid",
        "hdfc large cap", "hdfc large", "large cap", "large-cap", "large mid cap"
    ],
    "hdfc_mid_cap": [
        "hdfc mid cap opportunities", "mid cap opportunities", "hdfc mid cap", "hdfc mid",
        "mid cap", "mid-cap", "midcap"
    ],
    "hdfc_small_cap": [
        "hdfc small cap", "hdfc small", "small cap", "small-cap", "smallcap"
    ],
    "hdfc_silver_etf_fof": [
        "hdfc silver etf fof", "hdfc silver etf", "hdfc silver fund", "hdfc silver",
        "silver etf fof", "silver etf", "silver fund", "silver fof", "silver"
    ],
    "hdfc_multi_cap": [
        "hdfc multi cap", "hdfc multi", "multi cap", "multi-cap", "multicap"
    ],
}

# Financial topic keywords
TOPIC_KEYWORDS = {
    "expense_ratio": [
        "expense ratio", "total expense ratio", "ter", "management fee", "charges", "annual fee"
    ],
    "exit_load": [
        "exit load", "redemption charge", "redemption fee", "exit penalty", "penalty for withdrawal", "exit load period"
    ],
    "minimum_investment": [
        "minimum additional investment", "additional investment", "minimum sip", "minimum investment",
        "minimum lumpsum", "min sip", "min lumpsum", "min additional", "sip amount"
    ],
    "lock_in": [
        "lock-in", "lock in", "lock in period", "locked", "holding period"
    ],
    "benchmark": [
        "benchmark", "benchmark index", "index", "nifty"
    ],
    "fund_manager": [
        "fund manager", "who manages", "portfolio manager", "manager name", "managed by"
    ],
    "holdings": [
        "holdings", "portfolio", "stocks", "companies", "top 10", "top holdings", "allocation", "invested in"
    ],
    "nav": [
        "nav", "net asset value", "aum", "fund size", "asset size"
    ],
    "taxation": [
        "capital gains tax", "capital gains", "tax", "taxation", "stcg", "ltcg", "stamp duty"
    ],
}

# Regex patterns for detecting advisory, comparative, subjective, or speculative queries
ADVISORY_REGEX_PATTERNS = [
    r"\bshould\s+i\s+(invest|buy|sell|switch|redeem|start|stop)\b",
    r"\bwhich\s+(?:fund|scheme|one)?\s*(?:is\s+)?(more\s+profitable|better|best|good|suitable|safest|recommended|riskier|higher)\b",
    r"\b(recommend|recommendation|suggest|suggestion|advice|advise)\b",
    r"\b(expected|predict|forecast|future|target)\s+(return|growth|performance|cagr|nav)\b",
    r"\bwill\b.{1,50}\b(grow|rise|fall|perform|give|increase|decrease|gain)\b",
    r"\b(compare|comparison|versus|vs\.?)\b.{0,50}\b(fund|scheme)\b",
    r"\bwhich\s+is\s+(safer|riskier|better|more\s+profitable)\b",
    r"\bshould\s+i\s+put\s+my\s+money\b",
    r"\bgood\s+for\s+(long|short)\s+term\b",
    r"\bis\s+(this|the)\s+(fund|scheme)\s+(good|safe|worth\s+investing)\b",
    r"\bhow\s+much\s+(returns?|profit)\s+will\s+i\s+(get|make|earn)\b",
    r"\bcan\s+i\s+expect\b.{0,30}\b(returns?|cagr)\b",
    r"\bwould\s+you\s+advise\b",
]

COMPILED_ADVISORY = [re.compile(p, re.IGNORECASE) for p in ADVISORY_REGEX_PATTERNS]

from src.retrieval.entity_extractor import extract_scheme_id, extract_topic


def classify_intent_regex(query: str) -> Tuple[bool, Optional[str]]:
    """Fast regex-based intent classification (< 1ms).
    
    Returns:
        (is_advisory: bool, refusal_reason: Optional[str])
    """
    for regex in COMPILED_ADVISORY:
        if regex.search(query):
            logger.info(f"Regex classified query as ADVISORY: '{query}'")
            return True, "advisory"
    return False, None


def classify_intent_llm(query: str) -> bool:
    """Fallback LLM-based intent classifier using Groq for ambiguous queries.
    
    Returns True if advisory, False if purely factual.
    """
    api_key = config.groq_api_key or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        logger.info("Groq API key not set; defaulting to regex-only intent gate.")
        return False

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        system_prompt = (
            "You are a strict financial compliance gatekeeper for a facts-only mutual fund FAQ assistant.\n"
            "Classify the user query into exactly one category:\n"
            "- FACTUAL: Asking for objective parameters (NAV, expense ratio, exit load, minimum SIP, benchmark, fund manager, lock-in, holdings).\n"
            "- ADVISORY: Asking for recommendations, opinions, advice ('should I buy'), comparisons ('which is better'), returns forecasts, or suitability.\n"
            "Respond ONLY with the single word FACTUAL or ADVISORY."
        )
        response = client.chat.completions.create(
            model=config.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            max_tokens=10,
        )
        answer = response.choices[0].message.content.strip().upper()
        is_adv = "ADVISORY" in answer
        logger.info(f"LLM classified query as {answer} (is_advisory={is_adv})")
        return is_adv
    except Exception as e:
        logger.warning(f"Groq intent classification failed: {e}; falling back to safe factual path.")
        return False


def classify_intent(query: str) -> QueryIntentResult:
    """Classify user query into Factual or Advisory, extracting scheme & topic entities.
    
    Pipeline:
    1. Regex Fast-Path check for advisory patterns.
    2. Optional LLM fallback if ambiguous.
    3. Entity extraction for scheme_id and topic.
    """
    scheme_id = extract_scheme_id(query)
    topic = extract_topic(query)

    # Stage A: Regex fast-path
    is_adv_regex, reason = classify_intent_regex(query)
    if is_adv_regex:
        return QueryIntentResult(
            original_query=query,
            is_factual=False,
            is_advisory=True,
            has_pii=False,
            detected_scheme_id=scheme_id,
            detected_topic=topic,
            refusal_reason="advisory",
            classification_method="regex",
        )

    # If query has no financial topic and no scheme, check if it's an off-topic / advisory query via LLM
    is_adv_llm = False
    method = "regex"
    
    # Trigger LLM fallback only if query contains advisory trigger words like 'good', 'buy', 'better'
    soft_advisory_triggers = ["better", "best", "good", "suggest", "compare", "performance"]
    if any(t in query.lower() for t in soft_advisory_triggers):
        is_adv_llm = classify_intent_llm(query)
        method = "hybrid"

    if is_adv_llm:
        return QueryIntentResult(
            original_query=query,
            is_factual=False,
            is_advisory=True,
            has_pii=False,
            detected_scheme_id=scheme_id,
            detected_topic=topic,
            refusal_reason="advisory",
            classification_method="hybrid",
        )

    # Query is factual
    return QueryIntentResult(
        original_query=query,
        is_factual=True,
        is_advisory=False,
        has_pii=False,
        detected_scheme_id=scheme_id,
        detected_topic=topic,
        refusal_reason=None,
        classification_method=method,
    )
