"""Semantic section-atomic chunker for mutual fund structured documents."""

from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from src.state.models import DocumentChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


def slugify(text: str) -> str:
    """Convert arbitrary text into a clean alphanumeric slug with underscores.
    
    Example:
        'Expense Ratio & Exit Load' -> 'expense_ratio_exit_load'
    """
    clean = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "_", clean).strip("_")


def estimate_token_count(text: str) -> int:
    """Conservative token estimation based on character and sub-word heuristic.
    
    Average English/financial tokens are approximately 3.8 characters or 0.75 words.
    """
    if not text:
        return 0
    char_est = int(len(text) / 3.8)
    word_est = int(len(text.split()) * 1.3)
    return max(char_est, word_est)


SECTION_TOPIC_DESCRIPTORS = {
    "Expense Ratio & Exit Load": "Expense Ratio, Total Expense Ratio (TER), Management Fees, Exit Load, Stamp Duty, and Redemption Terms",
    "Minimum Investment & Lock-in": "Minimum Investment Amounts, SIP and Lumpsum minimums, Additional Investment, and Lock-in Period",
    "Fund Overview & Benchmark": "Fund Overview, Benchmark Index, AUM Fund Size, NAV, Riskometer, and Launch Date",
    "Fund Management": "Fund Managers, Experience, Tenure, and Portfolio Management Team",
    "Holdings & Portfolio Allocation": "Top Portfolio Holdings, Stock Allocations, Sector Allocation, and Asset Breakdown",
    "Investment Objective & Strategy": "Scheme Statutory Investment Objective and Asset Allocation Strategy",
}


def build_breadcrumb_header(scheme_name: str, category: str, section: str) -> str:
    """Build semantic breadcrumb context prepended to every indexed chunk."""
    descriptor = SECTION_TOPIC_DESCRIPTORS.get(section, "")
    desc_line = f"Topic: {descriptor}\n\n" if descriptor else "\n"
    return f"### Scheme: {scheme_name} | Category: {category} | Section: {section}\n{desc_line}"


def split_markdown_table(
    table_content: str,
    max_tokens: int = 500,
) -> List[str]:
    """Split an oversized Markdown table row-wise, replicating header rows in each part.
    
    Tables <= max_tokens are preserved as a single atomic chunk.
    """
    lines = [line.strip() for line in table_content.strip().split("\n") if line.strip()]
    if not lines or not lines[0].startswith("|"):
        return [table_content]

    # Check if whole table fits
    if estimate_token_count(table_content) <= max_tokens or len(lines) <= 3:
        return [table_content]

    # Header is typically line 0 (columns) and line 1 (delimiters |---|)
    header_lines = lines[:2]
    data_rows = lines[2:]

    chunks: List[str] = []
    current_rows: List[str] = []

    for row in data_rows:
        candidate_table = "\n".join(header_lines + current_rows + [row])
        if estimate_token_count(candidate_table) > max_tokens and current_rows:
            chunks.append("\n".join(header_lines + current_rows))
            current_rows = [row]
        else:
            current_rows.append(row)

    if current_rows:
        chunks.append("\n".join(header_lines + current_rows))

    return chunks if chunks else [table_content]


def chunk_section_block(
    block: Dict[str, Any],
    category: str,
    max_tokens: int = 500,
) -> List[DocumentChunk]:
    """Chunk a structured section block, prepending context breadcrumbs and attaching metadata.
    
    Tables <= 500 tokens remain strictly atomic.
    """
    scheme_id = block["scheme_id"]
    scheme_name = block["scheme_name"]
    source_url = block["source_url"]
    section = block["section"]
    content_type = block.get("content_type", "table" if "|" in block["content"] else "text")
    raw_content = block["content"].strip()
    
    # Resolve publish date
    raw_date = block.get("publish_date")
    if isinstance(raw_date, date):
        canonical_date = raw_date
    elif isinstance(raw_date, str):
        try:
            canonical_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
        except ValueError:
            canonical_date = date.today()
    else:
        canonical_date = date.today()

    section_slug = slugify(section)
    breadcrumb = build_breadcrumb_header(scheme_name, category, section)

    # Split if table or text exceeds max_tokens (empirical data shows tables are 48-456 tokens)
    if content_type == "table":
        sub_contents = split_markdown_table(raw_content, max_tokens=max_tokens)
    else:
        sub_contents = [raw_content]

    chunks: List[DocumentChunk] = []
    for idx, sub_content in enumerate(sub_contents):
        prefixed_content = breadcrumb + sub_content
        token_count = estimate_token_count(prefixed_content)
        chunk_id = f"{scheme_id}_{section_slug}_{idx}"

        chunk = DocumentChunk(
            chunk_id=chunk_id,
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            category=category,
            doc_type="GrowwPage",
            source_url=source_url,
            groww_url=source_url,
            publish_date=canonical_date,
            section=section,
            content=prefixed_content,
            content_type=content_type,
            page_number=None,
            token_count=token_count,
        )
        chunks.append(chunk)

    return chunks


def chunk_document(
    content_blocks: List[Dict[str, Any]],
    category: str,
    max_tokens: int = 500,
) -> List[DocumentChunk]:
    """Process a list of structured content blocks into validated DocumentChunk objects.
    
    Args:
        content_blocks: Structured blocks produced by parse_groww_page.
        category: Asset category (e.g., 'Equity: Mid Cap').
        max_tokens: Maximum tokens allowed before table row splitting.
        
    Returns:
        List of DocumentChunk models ready for vector indexing.
    """
    document_chunks: List[DocumentChunk] = []

    for block in content_blocks:
        sub_chunks = chunk_section_block(block, category=category, max_tokens=max_tokens)
        document_chunks.extend(sub_chunks)

    logger.info(
        f"Generated {len(document_chunks)} DocumentChunks for {content_blocks[0].get('scheme_id', 'unknown') if content_blocks else 'empty'}"
    )
    return document_chunks
