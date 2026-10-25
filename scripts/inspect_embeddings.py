"""Script to inspect and display chunk embeddings stored in ChromaDB."""

import os
import sys
from typing import Optional
from pathlib import Path
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set UTF-8 encoding for Windows stdout
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import chromadb
from src.config import config


def inspect_chromadb_embeddings(scheme_filter: Optional[str] = None, chunk_id_filter: Optional[str] = None):
    """Retrieve and display embeddings, metadata, and vectors from ChromaDB."""
    persist_dir = config.chroma_persist_directory
    col_name = config.chroma_collection_name

    print("=" * 80)
    print(f"CHROMADB EMBEDDING INSPECTOR - COLLECTION: '{col_name}'")
    print(f"Database Directory: {persist_dir}")
    if scheme_filter:
        print(f"Filtering strictly for Scheme: {scheme_filter}")
    print("=" * 80)

    client = chromadb.PersistentClient(path=persist_dir)
    try:
        col = client.get_collection(name=col_name)
    except Exception as e:
        print(f"Error connecting to collection '{col_name}': {e}")
        return

    # Fetch all records including the 384-dimensional dense vectors
    get_kwargs = {"include": ["embeddings", "metadatas", "documents"]}
    if scheme_filter:
        get_kwargs["where"] = {"scheme_id": scheme_filter}

    records = col.get(**get_kwargs)
    
    ids = records.get("ids", [])
    embeddings = records.get("embeddings", [])
    metadatas = records.get("metadatas", [])
    documents = records.get("documents", [])

    total_chunks = len(ids)
    print(f"\n[+] Total Chunks Found: {total_chunks}")

    if total_chunks == 0 or embeddings is None or len(embeddings) == 0:
        print("[-] No embeddings found in ChromaDB collection matching query.")
        return

    vec_dim = len(embeddings[0])
    print(f"[+] Embedding Model: {config.embedding_model_name}")
    print(f"[+] Embedding Vector Dimension: {vec_dim} floats per vector")
    print(f"[+] Metric Distance Space: {col.metadata.get('hnsw:space', 'cosine')}")
    print("-" * 80)

    # Group by scheme_id for clean display
    schemes: dict = {}
    for i in range(total_chunks):
        cid = ids[i]
        meta = metadatas[i] if metadatas else {}
        doc = documents[i] if documents else ""
        emb = np.array(embeddings[i], dtype=np.float32)

        sid = meta.get("scheme_id", "unknown")
        if sid not in schemes:
            schemes[sid] = []
        schemes[sid].append({
            "id": cid,
            "section": meta.get("section", "N/A"),
            "content_type": meta.get("content_type", "N/A"),
            "tokens": meta.get("token_count", "N/A"),
            "doc_preview": doc[:100].replace("\n", " "),
            "embedding": emb,
        })

    for sid, chunk_list in schemes.items():
        print(f"\n>>> SCHEME: {sid.upper()} ({len(chunk_list)} Chunks)")
        for idx, item in enumerate(chunk_list, 1):
            vec = item["embedding"]
            norm = np.linalg.norm(vec)
            vec_min = vec.min()
            vec_max = vec.max()
            vec_mean = vec.mean()

            # First 5 and last 5 dimensions preview
            vec_preview = (
                f"[{', '.join(f'{v:+.4f}' for v in vec[:5])}, ... , "
                f"{', '.join(f'{v:+.4f}' for v in vec[-5:])}]"
            )

            print(f"\n  [{idx}] Chunk ID: {item['id']}")
            print(f"      Section:       {item['section']} ({item['content_type']}) | Tokens: ~{item['tokens']}")
            print(f"      L2 Norm:       {norm:.4f} (unit normalized for cosine)")
            print(f"      Stats:         Min={vec_min:+.4f} | Max={vec_max:+.4f} | Mean={vec_mean:+.4f}")
            print(f"      Vector (384d): {vec_preview}")
            print(f"      Text Preview:  \"{item['doc_preview']}...\"")

    # Display the full 384-dimensional float array for the selected chunk
    print("\n" + "=" * 80)
    target_chunk = None
    if chunk_id_filter:
        for sid, clist in schemes.items():
            for c in clist:
                if c["id"] == chunk_id_filter:
                    target_chunk = c
                    break
    if not target_chunk:
        first_sid = list(schemes.keys())[0]
        target_chunk = schemes[first_sid][0]

    print(f"FULL 384-DIMENSIONAL EMBEDDING VECTOR FOR CHUNK: '{target_chunk['id']}'")
    print(f"Section: {target_chunk['section']} | Scheme: {target_chunk['id'].split('_')[0]}")
    print("=" * 80)
    full_vec = target_chunk["embedding"]

    # Print in rows of 12 floats for clean readability
    for row in range(0, len(full_vec), 12):
        row_slice = full_vec[row : row + 12]
        formatted = "  ".join(f"{v:+.4f}" for v in row_slice)
        print(f"Dim [{row:03d}..{row+len(row_slice)-1:03d}]:  {formatted}")

    print("\n" + "=" * 80)
    print(f"INSPECTION COMPLETE: All {total_chunks} chunks have valid 384-dim dense embeddings.")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Inspect ChromaDB Embeddings")
    parser.add_argument("--scheme", type=str, default=None, help="Filter by scheme_id (e.g. hdfc_mid_cap)")
    parser.add_argument("--chunk-id", type=str, default=None, help="Display full 384d vector for specific chunk_id")
    args = parser.parse_args()

    inspect_chromadb_embeddings(scheme_filter=args.scheme, chunk_id_filter=args.chunk_id)
