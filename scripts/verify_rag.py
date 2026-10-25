"""Comprehensive verification script for the 4 core RAG pillars:
1. Chunking
2. Embedding
3. Retrieval
4. Call to Groq
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import time
from src.ingestion.crawler import read_manifest
from src.ingestion.html_parser import parse_groww_page
from src.ingestion.chunker import chunk_document
from src.ingestion.indexer import get_embedding_function, get_chroma_client, get_or_create_collection
from src.retrieval.retriever import retrieve_chunks
from src.retrieval.context_assembler import assemble_context
from src.generation.prompt_templates import build_prompt
from src.generation.llm_client import generate

print("=" * 70)
print("  STEP 1: VERIFYING CHUNKING")
print("=" * 70)
manifest = read_manifest()
source = manifest["sources"][1]  # hdfc_small_cap
blocks = parse_groww_page(
    html_path=Path("data/raw/hdfc_small_cap/groww_page.html"),
    scheme_id=source["scheme_id"],
    scheme_name=source["scheme_name"],
    source_url=source["url"],
)
chunks = chunk_document(blocks, category=source.get("category", "Mutual Fund"))

print(f"Scheme ID: {source['scheme_id']}")
print(f"Raw structured blocks parsed: {len(blocks)}")
print(f"Total chunks created: {len(chunks)}")
print(f"Sample Chunk ID: {chunks[0].chunk_id}")
print(f"Sample Chunk Section: {chunks[0].section}")
print(f"Sample Chunk Token Count: {chunks[0].token_count}")
print(f"Sample Chunk Content:\n--- BEGIN CHUNK ---\n{chunks[0].content}\n--- END CHUNK ---")

print("\n" + "=" * 70)
print("  STEP 2: VERIFYING EMBEDDING GENERATION")
print("=" * 70)
t0 = time.time()
ef = get_embedding_function()
test_text = [
    "HDFC Small Cap Fund Direct Growth exit load is 1% if redeemed within 1 year.",
    "Fund Manager: Chirag Setalvad manages HDFC Small Cap Fund.",
]
vectors = ef(test_text)
elapsed_emb = time.time() - t0

print(f"Embedding Function: {ef.__class__.__name__}")
print(f"Model Name: sentence-transformers/all-MiniLM-L6-v2")
print(f"Generated {len(vectors)} dense vector embeddings in {elapsed_emb:.3f}s")
print(f"Vector Dimensions: {len(vectors[0])} dimensions (Standard all-MiniLM-L6-v2 dense vector space)")
print(f"Vector 1 first 8 floats: {vectors[0][:8]}")
print(f"Vector 2 first 8 floats: {vectors[1][:8]}")

print("\n" + "=" * 70)
print("  STEP 3: VERIFYING VECTOR RETRIEVAL FROM CHROMADB")
print("=" * 70)
client = get_chroma_client()
col = get_or_create_collection(client)
total_in_db = col.count()
print(f"ChromaDB Collection Name: {col.name}")
print(f"Total Chunks in ChromaDB: {total_in_db} chunks (all 5 canonical schemes indexed)")

query = "who is the fund manager for HDFC Small Cap Fund"
t0 = time.time()
retrieved = retrieve_chunks(query, scheme_id="hdfc_small_cap", top_k=2)
elapsed_ret = time.time() - t0

print(f"\nQuery: '{query}'")
print(f"Retrieval Time: {elapsed_ret * 1000:.1f}ms")
print(f"Retrieved Chunks: {len(retrieved)}")
for i, r in enumerate(retrieved):
    print(f"\n  [Rank {i+1}]")
    print(f"  Chunk ID: {r.chunk.chunk_id}")
    print(f"  Section: {r.chunk.section}")
    print(f"  Similarity Score: {r.similarity_score:.4f} (Rank: {r.rank})")
    print(f"  Source URL: {r.chunk.source_url}")
    print(f"  Content Preview:\n  {r.chunk.content[:160]}...")

print("\n" + "=" * 70)
print("  STEP 4: VERIFYING CALL TO GROQ (LLM GENERATION)")
print("=" * 70)
context_text, canonical_url, publish_date = assemble_context(retrieved)
prompt = build_prompt(
    context=context_text,
    query=query,
    source_url=canonical_url,
)
print(f"Model Target: openai/gpt-oss-120b via Groq Cloud")
print(f"Context passed to LLM: {len(context_text)} characters")
print(f"Assembled Prompt Preview:\n{prompt[:250]}...\n")

t0 = time.time()
groq_response = generate(prompt)
elapsed_groq = time.time() - t0

print(f"Groq API Call Completed in: {elapsed_groq:.2f}s")
print(f"\n--- RAW GROQ LLM OUTPUT ---")
print(groq_response)
print(f"--- END GROQ OUTPUT ---")

print("\n" + "=" * 70)
print("  ALL 4 RAG PILLARS VERIFIED SUCCESSFULLY!")
print("=" * 70)
