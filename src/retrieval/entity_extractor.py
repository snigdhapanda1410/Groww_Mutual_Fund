"""Entity extractor for mapping natural language user queries to scheme IDs and financial topics."""

import re
from typing import Optional, Tuple
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Scheme alias mapping (longest aliases first to prevent substring collision)
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
    "exit_load": [
        "exit load period", "exit loads", "exit load", "redemption charges", "redemption charge",
        "redemption fees", "redemption fee", "exit penalties", "exit penalty", "penalty for withdrawal"
    ],
    "expense_ratio": [
        "total expense ratio", "total expense ratios", "expense ratio", "expense ratios",
        "ter", "management fees", "management fee", "annual fees", "annual fee",
        "annual charges", "charges"
    ],
    "minimum_investment": [
        "minimum additional investment", "additional investment", "minimum sip", "minimum investment",
        "minimum lumpsum", "min sip", "min lumpsum", "min additional", "sip amount", "investment amount"
    ],
    "lock_in": [
        "lock-in period", "lock in period", "lock-in", "lock in", "elss lock", "locked", "holding period"
    ],
    "benchmark": [
        "benchmark index", "benchmark", "index", "nifty", "sensex"
    ],
    "riskometer": [
        "riskometer", "risk level", "risk grade", "risk category", "risk rating", "risk meter"
    ],
    "cas": [
        "consolidated account statement", "account statement", "cas"
    ],
    "capital_gains": [
        "capital gains tax", "capital gains", "tax statement", "elss tax", "80c",
        "taxation", "stcg", "ltcg", "stamp duty", "tax"
    ],
    "fund_manager": [
        "portfolio managers", "portfolio manager", "fund managers", "fund manager",
        "who manages", "manager name", "managed by"
    ],
    "holdings": [
        "top holdings", "top 10", "holdings", "portfolio", "stocks", "companies", "allocation", "invested in"
    ],
    "nav": [
        "net asset value", "nav", "aum", "fund size", "asset size"
    ],
}

# Pre-sort all (alias, scheme_id) pairs by alias length descending
_SORTED_SCHEME_PAIRS = []
for _sid, _aliases in SCHEME_ALIASES.items():
    for _alias in _aliases:
        _SORTED_SCHEME_PAIRS.append((_alias, _sid))
_SORTED_SCHEME_PAIRS.sort(key=lambda pair: len(pair[0]), reverse=True)

# Pre-sort all (keyword, topic) pairs by keyword length descending
_SORTED_TOPIC_PAIRS = []
for _topic, _keywords in TOPIC_KEYWORDS.items():
    for _kw in _keywords:
        _SORTED_TOPIC_PAIRS.append((_kw, _topic))
_SORTED_TOPIC_PAIRS.sort(key=lambda pair: len(pair[0]), reverse=True)


def extract_scheme_id(query: str) -> Optional[str]:
    """Identify which of the 5 canonical Groww schemes is referenced in the query.
    
    Checks longest aliases first to avoid substring confusion (e.g. 'large and mid cap' 
    takes precedence over 'mid cap').
    """
    if not query:
        return None
    clean_query = query.lower()
    for alias, scheme_id in _SORTED_SCHEME_PAIRS:
        pattern = rf"\b{re.escape(alias)}\b"
        if re.search(pattern, clean_query):
            return scheme_id
    return None


def extract_topic(query: str) -> Optional[str]:
    """Identify the financial parameter or topic category requested in the query.
    
    Checks longest keywords first.
    """
    if not query:
        return None
    clean_query = query.lower()
    for kw, topic in _SORTED_TOPIC_PAIRS:
        pattern = rf"\b{re.escape(kw)}\b"
        if re.search(pattern, clean_query):
            return topic
    return None


def extract_entities(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract both scheme_id and topic entities from user query.
    
    Returns:
        (scheme_id, topic)
    """
    scheme_id = extract_scheme_id(query)
    topic = extract_topic(query)
    logger.info(f"Extracted entities for query '{query[:60]}...': scheme_id='{scheme_id}', topic='{topic}'")
    return scheme_id, topic
