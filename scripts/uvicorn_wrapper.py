#!/usr/bin/env python3
"""Uvicorn CLI wrapper that safely sanitizes raw environment variable tokens like $PORT and enforces single-worker mode."""

import os
import sys
import uvicorn.main

# Force single-worker and offline cache paths regardless of cloud platform defaults
os.environ["WEB_CONCURRENCY"] = "1"
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HOME", "/app/data/cache/huggingface")
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", "/app/data/cache/sentence_transformers")
os.environ.setdefault("NLTK_DATA", "/app/data/cache/nltk_data")

raw_port = os.environ.get("PORT", "8000")
try:
    int(raw_port)
    port_str = raw_port
except (ValueError, TypeError):
    port_str = "8000"

new_argv = []
skip_next = False
has_workers = False

for i, arg in enumerate(sys.argv):
    if skip_next:
        skip_next = False
        continue
    # Force single worker to avoid Uvicorn Multiprocess supervisor death loops
    if arg in ("--workers", "-w") and i + 1 < len(sys.argv):
        new_argv.extend([arg, "1"])
        skip_next = True
        has_workers = True
    elif arg.startswith("--workers="):
        new_argv.append("--workers=1")
        has_workers = True
    elif arg.startswith("-w="):
        new_argv.append("-w=1")
        has_workers = True
    elif arg in ("--port", "-p") and i + 1 < len(sys.argv) and sys.argv[i + 1] in ("$PORT", "${PORT}"):
        new_argv.extend([arg, port_str])
        skip_next = True
    elif arg.startswith("--port=") and arg.split("=", 1)[1] in ("$PORT", "${PORT}"):
        new_argv.append(f"--port={port_str}")
    elif arg in ("$PORT", "${PORT}"):
        new_argv.append(port_str)
    else:
        new_argv.append(arg)

is_help_or_version = any(a in ("--help", "-h", "--version", "-v") for a in new_argv)
if not has_workers and len(new_argv) > 1 and not is_help_or_version:
    new_argv.extend(["--workers", "1"])

sys.argv = new_argv

if __name__ == "__main__":
    sys.exit(uvicorn.main.main())
