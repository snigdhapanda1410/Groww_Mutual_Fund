"""Optional reranker module supporting Reciprocal Rank Fusion (RRF) and pass-through."""

import re
from typing import List, Optional, Set

from src.config import config
from src.state.models import RetrievedContext
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Basic stopwords to filter out when computing query-chunk lexical overlap
STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by", "about",
    "is", "are", "was", "were", "of", "what", "which", "how", "much", "tell", "me",
    "does", "do", "can", "please", "fund", "hdfc", "mutual"
}


def _tokenize(text: str) -> Set[str]:
    """Extract lowercased alphanumeric tokens excluding stopwords."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\-]+\b", text.lower())
    return {t for t in tokens if len(t) > 1 and t not in STOPWORDS}


def rerank_chunks(
    query: str,
    chunks: List[RetrievedContext],
    use_reranker: Optional[bool] = None,
    rrf_k: int = 60,
) -> List[RetrievedContext]:
    """Rerank retrieved context chunks.
    
    If use_reranker is False (or defaults to config.use_reranker which is False),
    returns chunks in their original retrieved order with verified 1-indexed ranks.
    
    If use_reranker is True, applies Reciprocal Rank Fusion (RRF) combining:
    1. Vector similarity rank (dense ranking)
    2. Query term overlap lexical rank (sparse ranking)
    
    Args:
        query: User input query text.
        chunks: List of RetrievedContext chunks from the vector retriever.
        use_reranker: Override flag for enabling reranker.
        rrf_k: Smoothing constant for RRF (default: 60).
        
    Returns:
        List of reranked RetrievedContext objects with updated rank attributes.
    """
    if not chunks:
        return []

    should_rerank = (
        use_reranker if use_reranker is not None else getattr(config, "use_reranker", False)
    )

    if not should_rerank or len(chunks) <= 1:
        # Pass-through: maintain vector retrieval order, guarantee 1-indexed ranks
        for idx, rc in enumerate(chunks, 1):
            rc.rank = idx
        return chunks

    logger.info(
        f"Applying RRF reranker on {len(chunks)} chunks for query: '{query[:50]}...'"
    )
    query_tokens = _tokenize(query)

    # 1. Vector ranking (input order is assumed ordered by similarity score descending)
    # 2. Lexical scoring based on query token overlap with chunk content and section
    scored_lexical = []
    for rc in chunks:
        content_tokens = _tokenize(rc.chunk.content) | _tokenize(rc.chunk.section)
        overlap = len(query_tokens & content_tokens)
        if overlap > 0:
            scored_lexical.append((rc, overlap))

    # Sort chunks with positive overlap descending (stable sort preserves vector rank on tie)
    scored_lexical.sort(key=lambda item: item[1], reverse=True)
    lexical_rank_map = {
        item[0].chunk.chunk_id: rank for rank, item in enumerate(scored_lexical, 1)
    }

    # 3. Compute Reciprocal Rank Fusion (RRF) score: 1/(k + r_vec) + (1/(k + r_lex) if matched else 0)
    fused_chunks = []
    for vec_rank, rc in enumerate(chunks, 1):
        rrf_score = 1.0 / (rrf_k + vec_rank)
        if rc.chunk.chunk_id in lexical_rank_map:
            lex_rank = lexical_rank_map[rc.chunk.chunk_id]
            rrf_score += 1.0 / (rrf_k + lex_rank)
        fused_chunks.append((rc, rrf_score))

    # Sort descending by RRF score
    fused_chunks.sort(key=lambda item: item[1], reverse=True)

    # Update ranks and return
    reranked: List[RetrievedContext] = []
    for new_rank, (rc, rrf_score) in enumerate(fused_chunks, 1):
        rc.rank = new_rank
        reranked.append(rc)
        logger.debug(
            f"Chunk '{rc.chunk.chunk_id}' -> Rank {new_rank} (RRF: {rrf_score:.5f})"
        )

    return reranked
