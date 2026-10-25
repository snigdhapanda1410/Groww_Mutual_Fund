"""PII Redaction Interceptor for Indian Financial Identifiers."""

import re
from typing import Optional, Tuple
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Regular expression patterns for Indian financial PII
PII_PATTERNS = {
    # Permanent Account Number (PAN): 5 uppercase letters, 4 digits, 1 uppercase letter
    "PAN": r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b",
    
    # Aadhaar Number: 12 digits, often formatted as 4-4-4 with spaces or hyphens
    "Aadhaar": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    
    # Indian Mobile Phone Number: +91 or 0 prefix optional, starts with 6-9, followed by 9 digits
    "Mobile": r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b",
    
    # Email Address: Standard RFC 5322 simplified pattern
    "Email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    
    # Bank Account Number: explicit bank account or long contiguous account numbers
    "BankAccount": r"(?:\bbank\s*account|\ba\/c\b)[\s:#-]*(?:is\s*)?\d{9,18}\b|\b\d{13,18}\b",

    # Mutual Fund Folio Number: Explicit folio label or account no followed by 5 to 15 digits
    "Folio": r"\b(?:folio|folio\s*no|account\s*no)(?:\s+(?:is|number|no|#))?[\s:#-]*\d{5,15}\b",
}

# Compiled regex objects for speed
COMPILED_PATTERNS = {
    pii_type: re.compile(pattern, re.IGNORECASE if pii_type in ("Folio", "Email", "PAN", "BankAccount") else 0)
    for pii_type, pattern in PII_PATTERNS.items()
}


def detect_pii(query: str) -> Tuple[bool, Optional[str]]:
    """Scan query text for sensitive Indian financial PII.
    
    Args:
        query: User input query string.
        
    Returns:
        Tuple of (has_pii: bool, pii_type: Optional[str]).
    """
    if not query or not query.strip():
        return False, None

    # Check each PII type
    for pii_type, compiled_regex in COMPILED_PATTERNS.items():
        match = compiled_regex.search(query)
        if match:
            # Additional validation to prevent false positives for BankAccount on years or common numbers
            if pii_type == "BankAccount":
                matched_str = match.group()
                # If matched 10 digits starting with 6-9, it's already captured or mobile
                if len(matched_str) == 10 and matched_str[0] in "6789":
                    continue
                # If 9-18 digits, confirm it's not a standard phone or folio
                logger.warning(f"PII detected in user query: {pii_type}")
                return True, pii_type

            logger.warning(f"PII detected in user query: {pii_type}")
            return True, pii_type

    return False, None


def redact_pii(text: str) -> str:
    """Redact any detected PII tokens in text with placeholder tags for audit logging.
    
    Args:
        text: Input string potentially containing sensitive personal data.
        
    Returns:
        Sanitized string safe for persistent logging.
    """
    sanitized = text
    for pii_type, compiled_regex in COMPILED_PATTERNS.items():
        sanitized = compiled_regex.sub(f"[REDACTED_{pii_type.upper()}]", sanitized)
    return sanitized


def get_pii_block_response() -> str:
    """Return user-friendly refusal message when personal identification is detected."""
    return (
        "For your security, please do not share personal identification details such as PAN, "
        "Aadhaar, folio numbers, mobile numbers, or bank account information. "
        "I am a facts-only assistant and cannot access personal accounts or financial records."
    )
