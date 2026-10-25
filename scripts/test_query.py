"""Analyze why 'What's the expense ratio of HDFC large cap mutual fund?' retrieved objective vs expense ratio."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="./data/chromadb")
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
col = client.get_collection("hdfc_mutual_fund_facts", embedding_function=ef)

queries = [
    "What's the expense ratio of HDFC large cap mutual fund?",
    "expense ratio of HDFC large cap",
    "What is the expense ratio TER of HDFC large and mid cap fund?",
    "HDFC large cap expense ratio and exit load",
    "HDFC large cap TER direct plan"
]

print("=" * 80)
print("TESTING EXPENSE RATIO QUERY PHRASINGS ON 'hdfc_large_mid_cap':")
print("=" * 80)

for q in queries:
    res = col.query(
        query_texts=[q],
        n_results=6,
        where={"scheme_id": "hdfc_large_mid_cap"}
    )
    print(f"\nQuery: '{q}'")
    for i in range(len(res["ids"][0])):
        cid = res["ids"][0][i]
        dist = res["distances"][0][i]
        sec = res["metadatas"][0][i]["section"]
        is_target = " [TARGET]" if "expense_ratio" in cid else ""
        print(f"  Rank #{i+1}: {cid} (Dist: {dist:.4f}){is_target}")
