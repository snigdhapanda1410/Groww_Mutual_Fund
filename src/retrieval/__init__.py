"""Retrieval subsystem for entity extraction, vector search, and context assembly."""

from src.retrieval.entity_extractor import (
    SCHEME_ALIASES,
    TOPIC_KEYWORDS,
    extract_entities,
    extract_scheme_id,
    extract_topic,
)
from src.retrieval.retriever import (
    build_metadata_filter,
    retrieve_chunks,
)
from src.retrieval.reranker import (
    rerank_chunks,
)
from src.retrieval.context_assembler import (
    assemble_context,
)

__all__ = [
    "SCHEME_ALIASES",
    "TOPIC_KEYWORDS",
    "extract_entities",
    "extract_scheme_id",
    "extract_topic",
    "build_metadata_filter",
    "retrieve_chunks",
    "rerank_chunks",
    "assemble_context",
]
