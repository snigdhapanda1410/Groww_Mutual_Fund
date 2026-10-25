"""Standardized refusal response templates adhering to SEBI/AMFI compliance rules."""

from datetime import date
from typing import Optional


def get_advisory_refusal(as_of_date: Optional[date] = None) -> str:
    """Return compliant refusal for investment advice, recommendations, or predictions."""
    target_date = as_of_date or date.today()
    return (
        "I'm designed to answer only verified factual questions about HDFC Mutual Fund schemes "
        "— such as expense ratios, exit loads, SIP minimums, and lock-in periods. "
        "I cannot offer investment advice, fund recommendations, performance predictions, or fund comparisons.\n\n"
        "For guidance on evaluating mutual funds, please visit "
        "[AMFI - Mutual Funds Sahi Hai](https://www.amfiindia.com/investor-corner/knowledge-center) "
        "or [SEBI Investor Education](https://www.sebi.gov.in/investor.html).\n\n"
        f"*Last updated from sources: {target_date.strftime('%Y-%m-%d')}*"
    )


def get_out_of_scope_refusal(as_of_date: Optional[date] = None) -> str:
    """Return refusal when user asks about schemes outside the 5 covered HDFC schemes."""
    target_date = as_of_date or date.today()
    return (
        "I only cover factual queries for these 5 HDFC Mutual Fund schemes: "
        "Mid-Cap Opportunities, Small Cap, Large & Mid Cap, Silver ETF FoF, and Multi Cap (all Direct - Growth plans). "
        "The scheme you asked about is outside my current coverage.\n\n"
        "Please visit [Groww Mutual Funds](https://groww.in/mutual-funds) for information on other schemes.\n\n"
        f"*Last updated from sources: {target_date.strftime('%Y-%m-%d')}*"
    )


def get_pii_refusal() -> str:
    """Return refusal message when PII is detected."""
    return (
        "For your security, please do not share personal identification details such as PAN, "
        "Aadhaar, folio numbers, mobile numbers, or bank account information. "
        "I am a facts-only assistant and cannot access personal accounts or financial records."
    )


def get_off_topic_refusal(as_of_date: Optional[date] = None) -> str:
    """Return refusal when user asks completely unrelated non-financial questions."""
    target_date = as_of_date or date.today()
    return (
        "I am a specialized assistant designed to answer factual questions regarding 5 HDFC Mutual Fund schemes. "
        "I cannot assist with general knowledge, coding, politics, or unrelated topics.\n\n"
        "Please ask a question about scheme parameters such as expense ratio, exit load, minimum SIP, or portfolio holdings.\n\n"
        f"*Last updated from sources: {target_date.strftime('%Y-%m-%d')}*"
    )


def get_refusal_response(reason: str, as_of_date: Optional[date] = None) -> str:
    """Dispatcher returning appropriate compliance refusal based on classification reason.
    
    Args:
        reason: One of 'advisory', 'pii_detected', 'out_of_scope', or 'off_topic'.
        as_of_date: Optional statutory reference date.
    """
    clean_reason = reason.lower().strip()
    if clean_reason in ("advisory", "advice", "comparison", "recommendation", "prediction"):
        return get_advisory_refusal(as_of_date)
    elif clean_reason in ("pii", "pii_detected", "personal_data"):
        return get_pii_refusal()
    elif clean_reason in ("out_of_scope", "unsupported_scheme"):
        return get_out_of_scope_refusal(as_of_date)
    else:
        return get_off_topic_refusal(as_of_date)
