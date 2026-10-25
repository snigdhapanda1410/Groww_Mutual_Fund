"""ChromaDB indexing pipeline for HDFC Mutual Fund factual documents."""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Suppress Hugging Face Windows symlink warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import chromadb
from chromadb.utils import embedding_functions

from src.config import config
from src.ingestion.crawler import crawl_scheme, read_manifest
from src.ingestion.html_parser import parse_groww_page
from src.ingestion.chunker import chunk_document
from src.state.models import DocumentChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


_CHROMA_CLIENT: Optional[chromadb.PersistentClient] = None
_EMBEDDING_FUNCTION: Optional[Any] = None
_COLLECTION: Optional[Any] = None


def get_embedding_function(model_name: Optional[str] = None):
    """Initialize or return cached SentenceTransformer embedding function (singleton)."""
    global _EMBEDDING_FUNCTION
    target_model = model_name or config.embedding_model_name
    if _EMBEDDING_FUNCTION is None:
        logger.info(f"Loading SentenceTransformer model '{target_model}' into singleton cache...")
        # Prefer cached offline model weights to eliminate unauthenticated HuggingFace Hub network calls
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        try:
            _EMBEDDING_FUNCTION = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=target_model
            )
        except Exception as e:
            logger.warning(f"Offline model load failed ({e}), falling back to online hub check...")
            os.environ.pop("HF_HUB_OFFLINE", None)
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
            _EMBEDDING_FUNCTION = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=target_model
            )
    return _EMBEDDING_FUNCTION


def get_chroma_client(persist_path: Optional[str] = None) -> chromadb.PersistentClient:
    """Initialize or return cached local persistent ChromaDB client."""
    global _CHROMA_CLIENT
    target_path = Path(persist_path or config.chroma_persist_directory)
    target_path.mkdir(parents=True, exist_ok=True)
    if persist_path is not None:
        return chromadb.PersistentClient(path=str(target_path))
    if _CHROMA_CLIENT is None:
        _CHROMA_CLIENT = chromadb.PersistentClient(path=str(target_path))
    return _CHROMA_CLIENT


def get_or_create_collection(
    client: chromadb.PersistentClient,
    collection_name: Optional[str] = None,
    embedding_function: Optional[Any] = None,
    rebuild: bool = False,
):
    """Retrieve or create ChromaDB collection with cosine distance metric and singleton caching."""
    global _COLLECTION
    name = collection_name or config.chroma_collection_name
    ef = embedding_function or get_embedding_function()

    if rebuild:
        try:
            client.delete_collection(name=name)
            logger.info(f"Rebuild requested: Deleted existing ChromaDB collection '{name}'")
        except Exception:
            pass
        _COLLECTION = None

    if _COLLECTION is None or collection_name is not None or rebuild:
        col = client.get_or_create_collection(
            name=name,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        if collection_name is None and not rebuild:
            _COLLECTION = col
        return col

    return _COLLECTION


def index_chunks(
    collection: Any,
    chunks: List[DocumentChunk],
    batch_size: int = 50,
) -> int:
    """Upsert DocumentChunk models into ChromaDB in batches.
    
    Using collection.upsert ensures idempotency: re-indexing the same chunks
    overwrites rather than duplicating.
    """
    if not chunks:
        return 0

    total_indexed = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        ids = [c.chunk_id for c in batch]
        documents = [c.content for c in batch]
        metadatas = [
            {
                "scheme_id": c.scheme_id,
                "scheme_name": c.scheme_name,
                "category": c.category,
                "doc_type": c.doc_type,
                "source_url": str(c.source_url),
                "publish_date": c.publish_date.isoformat(),
                "section": c.section,
                "content_type": c.content_type,
                "token_count": c.token_count or 0,
            }
            for c in batch
        ]

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        total_indexed += len(batch)

    logger.info(f"Upserted {total_indexed} chunks into ChromaDB collection '{collection.name}'")
    return total_indexed


def index_scheme(
    scheme_id: str,
    client: Optional[chromadb.PersistentClient] = None,
    collection: Optional[Any] = None,
    rebuild: bool = False,
    force_crawl: bool = False,
) -> List[DocumentChunk]:
    """Execute end-to-end ingestion (crawl -> parse -> chunk -> index) for a single scheme."""
    manifest = read_manifest()
    entry = next((s for s in manifest.get("sources", []) if s["scheme_id"] == scheme_id), None)
    if not entry:
        raise ValueError(f"Scheme ID '{scheme_id}' not found in sources_manifest.json")

    url = entry["url"]
    scheme_name = entry["scheme_name"]
    category = entry.get("category", "Mutual Fund")
    html_path = Path(f"data/raw/{scheme_id}/groww_page.html")

    # Step 1: Ensure snapshot exists or force refresh
    if not html_path.exists() or rebuild or force_crawl:
        logger.info(f"Downloading HTML snapshot for {scheme_id} (force={force_crawl})...")
        crawl_scheme(entry, force=force_crawl)

    # Step 2: Parse structured blocks
    blocks = parse_groww_page(
        html_path=html_path,
        scheme_id=scheme_id,
        scheme_name=scheme_name,
        source_url=url,
    )

    # Step 3: Chunk blocks with breadcrumbs
    chunks = chunk_document(blocks, category=category)

    # Step 4: Index into ChromaDB
    chroma_client = client or get_chroma_client()
    chroma_col = collection or get_or_create_collection(chroma_client, rebuild=rebuild)
    index_chunks(chroma_col, chunks)

    return chunks


def index_all(
    rebuild: bool = False,
    persist_path: Optional[str] = None,
    force_crawl: bool = False,
) -> Dict[str, Any]:
    """Index strictly all 5 canonical Groww schemes defined in manifest.
    
    Args:
        rebuild: If True, purges existing ChromaDB collection before re-indexing.
        persist_path: Optional custom path for ChromaDB persistent storage.
        force_crawl: If True, forces fresh crawl of all 5 Groww scheme pages before indexing.
        
    Returns:
        Summary dict containing total chunks indexed and per-scheme breakdown.
    """
    manifest = read_manifest()
    sources = manifest.get("sources", [])
    logger.info(
        f"Starting corpus indexing for {len(sources)} schemes "
        f"(rebuild={rebuild}, force_crawl={force_crawl})..."
    )

    client = get_chroma_client(persist_path=persist_path)
    collection = get_or_create_collection(client, rebuild=rebuild)

    results: Dict[str, int] = {}
    total_chunks = 0

    for entry in sources:
        scheme_id = entry["scheme_id"]
        chunks = index_scheme(
            scheme_id=scheme_id,
            client=client,
            collection=collection,
            rebuild=False,  # Rebuild already handled at collection level
            force_crawl=force_crawl,
        )
        results[scheme_id] = len(chunks)
        total_chunks += len(chunks)

    final_count = collection.count()
    logger.info(f"Indexing complete! Collection count: {final_count} (New chunks: {total_chunks})")

    return {
        "status": "success",
        "total_sources": len(sources),
        "total_indexed_chunks": total_chunks,
        "collection_total_count": final_count,
        "schemes": results,
    }


def main():
    parser = argparse.ArgumentParser(description="ChromaDB Indexer for HDFC Mutual Fund FAQ Assistant")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild collection from scratch")
    parser.add_argument("--force-crawl", action="store_true", help="Force re-crawling of live Groww pages before indexing")
    parser.add_argument("--scheme", type=str, default=None, help="Index a specific scheme_id only")
    args = parser.parse_args()

    if args.scheme:
        chunks = index_scheme(scheme_id=args.scheme, rebuild=args.rebuild, force_crawl=args.force_crawl)
        print(f"Indexed {len(chunks)} chunks for {args.scheme}")
    else:
        summary = index_all(rebuild=args.rebuild, force_crawl=args.force_crawl)
        print("=== INDEXING SUMMARY ===")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
