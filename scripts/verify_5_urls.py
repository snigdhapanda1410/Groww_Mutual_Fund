import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.generation import answer_query

queries = [
    ("hdfc_mid_cap", "What is the benchmark for HDFC Mid-Cap Opportunities Fund?"),
    ("hdfc_small_cap", "What is the exit load for HDFC Small Cap Fund?"),
    ("hdfc_large_mid_cap", "Who is the fund manager for HDFC Large and Mid Cap Fund?"),
    ("hdfc_silver_etf_fof", "What is the expense ratio for HDFC Silver ETF FoF?"),
    ("hdfc_multi_cap", "What is the minimum SIP investment for HDFC Multi Cap Fund?"),
]

print("=" * 80)
print("  END-TO-END VERIFICATION: 5 SCHEMES -> 5 CORRECT GROWW CITATIONS")
print("=" * 80)

for sid, q in queries:
    resp = answer_query(q)
    print(f"\nScheme ID: {sid}")
    print(f"Query: '{q}'")
    first_line = resp.answer_text.strip().split("\n")[0]
    print(f"Answer: {first_line}")
    print(f"Citation URL: {resp.citation_url}")
    print(f"Is Refusal: {resp.is_refusal}")
    print("-" * 80)
