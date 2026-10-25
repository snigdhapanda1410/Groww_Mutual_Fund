"""Context assembler for structuring retrieved chunks into standardized LLM prompt blocks."""

from typing import List, Tuple

from src.state.models import RetrievedContext
from src.utils.logger import get_logger

logger = get_logger(__name__)


def assemble_context(chunks: List[RetrievedContext]) -> Tuple[str, str, str]:
    """Assemble a list of RetrievedContext chunks into structured context text for LLM prompts.
    
    Format:
        === CONTEXT {i} (Source: {doc_type} | Scheme: {scheme_name} | Date: {publish_date}) ===
        {content}
        
    Args:
        chunks: List of RetrievedContext chunks ordered by rank.
        
    Returns:
        Tuple of (context_text, canonical_url, publish_date):
            - context_text: Concatenated string of formatted context blocks separated by double newlines.
            - canonical_url: The primary source URL from the top-ranked chunk (or empty string).
            - publish_date: The ISO date string (YYYY-MM-DD) from the top-ranked chunk (or empty string).
    """
    if not chunks:
        logger.info("assemble_context called with empty chunk list; returning empty strings.")
        return "", "", ""

    context_parts: List[str] = []
    for i, rc in enumerate(chunks, 1):
        chunk = rc.chunk
        pub_date_str = (
            chunk.publish_date.strftime("%Y-%m-%d")
            if hasattr(chunk.publish_date, "strftime")
            else str(chunk.publish_date)
        )
        header = (
            f"=== CONTEXT {i} "
            f"(Source: {chunk.doc_type} | "
            f"Scheme: {chunk.scheme_name} | "
            f"Date: {pub_date_str}) ==="
        )
        context_parts.append(f"{header}\n{chunk.content}")

    # Top-ranked chunk provides primary source URL and canonical statutory publish date
    top_chunk = chunks[0].chunk
    canonical_url = str(top_chunk.source_url)
    primary_publish_date = (
        top_chunk.publish_date.strftime("%Y-%m-%d")
        if hasattr(top_chunk.publish_date, "strftime")
        else str(top_chunk.publish_date)
    )

    assembled_text = "\n\n".join(context_parts)
    logger.info(
        f"Assembled {len(chunks)} chunks into context text ({len(assembled_text)} chars, "
        f"url='{canonical_url}', date='{primary_publish_date}')"
    )

    return assembled_text, canonical_url, primary_publish_date
