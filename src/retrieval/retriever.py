"""Vector Retriever for querying ChromaDB with metadata filtering and confidence gating."""

from datetime import datetime, date
import time
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.utils import embedding_functions

from src.config import config
from src.ingestion.indexer import get_chroma_client, get_or_create_collection
from src.state.models import DocumentChunk, RetrievedContext
from src.utils.logger import get_logger

logger = get_logger(__name__)


def build_metadata_filter(
    scheme_id: Optional[str] = None,
    section: Optional[str] = None,
    doc_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Construct ChromaDB 'where' filtering clause based on available query metadata.
    
    Supports single or composite conditions using ChromaDB operator syntax ($eq, $and).
    """
    conditions: List[Dict[str, Any]] = []

    if scheme_id:
        conditions.append({"scheme_id": {"$eq": scheme_id}})
    if section:
        conditions.append({"section": {"$eq": section}})
    if doc_type:
        conditions.append({"doc_type": {"$eq": doc_type}})

    if not conditions:
        return None
    elif len(conditions) == 1:
        return conditions[0]
    else:
        return {"$and": conditions}


def retrieve_chunks(
    query: str,
    scheme_id: Optional[str] = None,
    section: Optional[str] = None,
    top_k: Optional[int] = None,
    similarity_threshold: Optional[float] = None,
    collection: Optional[Any] = None,
) -> List[RetrievedContext]:
    """Execute metadata-filtered vector search against ChromaDB with confidence gating.
    
    Args:
        query: User input query text.
        scheme_id: Optional target canonical scheme ID for isolation (e.g., 'hdfc_mid_cap').
        section: Optional section filter (e.g., 'Expense Ratio & Exit Load').
        top_k: Number of chunks to retrieve (defaults to config.retrieval_top_k = 3).
        similarity_threshold: Maximum cosine distance allowed (defaults to config.similarity_threshold = 0.65).
        collection: Optional ChromaDB collection instance.
        
    Returns:
        List of RetrievedContext objects ordered by relevance rank.
    """
    start_time = time.perf_counter()
    k = top_k or config.retrieval_top_k
    threshold = similarity_threshold if similarity_threshold is not None else config.similarity_threshold

    if not query or not query.strip():
        logger.warning("Empty query passed to retrieve_chunks; returning empty list.")
        return []

    # Connect to persistent ChromaDB collection
    if collection is None:
        client = get_chroma_client()
        col = get_or_create_collection(client)
    else:
        col = collection

    where_clause = build_metadata_filter(scheme_id=scheme_id, section=section)

    query_params: Dict[str, Any] = {
        "query_texts": [query],
        "n_results": k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_clause:
        query_params["where"] = where_clause

    try:
        raw_results = col.query(**query_params)
    except Exception as e:
        logger.error(f"ChromaDB query execution error: {e}")
        return []

    retrieved: List[RetrievedContext] = []
    ids = raw_results.get("ids", [[]])[0]
    docs = raw_results.get("documents", [[]])[0]
    metas = raw_results.get("metadatas", [[]])[0]
    distances = raw_results.get("distances", [[]])[0]

    for rank_idx, (cid, doc_text, meta, dist) in enumerate(zip(ids, docs, metas, distances), 1):
        # Cosine distance confidence gate: distance > 0.65 is rejected as low-confidence
        if dist > threshold:
            logger.info(
                f"Chunk '{cid}' rejected: distance {dist:.4f} > threshold {threshold:.2f}."
            )
            continue

        raw_date_str = meta.get("publish_date", "2026-10-25")
        try:
            pub_date = datetime.strptime(raw_date_str[:10], "%Y-%m-%d").date()
        except ValueError:
            pub_date = date.today()

        doc_chunk = DocumentChunk(
            chunk_id=cid,
            scheme_id=meta.get("scheme_id", scheme_id or "unknown"),
            scheme_name=meta.get("scheme_name", "HDFC Mutual Fund"),
            category=meta.get("category", "Mutual Fund"),
            doc_type=meta.get("doc_type", "GrowwPage"),
            source_url=meta.get("source_url", "https://groww.in/mutual-funds"),
            groww_url=meta.get("source_url", "https://groww.in/mutual-funds"),
            publish_date=pub_date,
            section=meta.get("section", "General"),
            content=doc_text,
            content_type=meta.get("content_type", "text"),
            page_number=None,
            token_count=int(meta.get("token_count", len(doc_text.split()))),
        )

        sim_score = max(0.0, 1.0 - float(dist))
        retrieved.append(
            RetrievedContext(
                chunk=doc_chunk,
                similarity_score=round(sim_score, 4),
                rank=rank_idx,
            )
        )

    latency_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"Retrieved {len(retrieved)}/{len(ids)} valid chunks in {latency_ms:.1f}ms "
        f"(scheme_id='{scheme_id}', query='{query[:40]}...')"
    )

    return retrieved
