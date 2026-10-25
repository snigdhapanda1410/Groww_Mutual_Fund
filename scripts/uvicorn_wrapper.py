#!/usr/bin/env python3
"""Uvicorn CLI wrapper that safely sanitizes raw environment variable tokens like $PORT and enforces timeouts."""

import os
import sys
import uvicorn.main

os.environ.setdefault("WEB_CONCURRENCY", "1")
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
has_healthcheck_timeout = False

for i, arg in enumerate(sys.argv):
    if skip_next:
        skip_next = False
        continue
    if "--timeout-worker-healthcheck" in arg:
        has_healthcheck_timeout = True
    if arg in ("--port", "-p") and i + 1 < len(sys.argv) and sys.argv[i + 1] in ("$PORT", "${PORT}"):
        new_argv.extend([arg, port_str])
        skip_next = True
    elif arg.startswith("--port=") and arg.split("=", 1)[1] in ("$PORT", "${PORT}"):
        new_argv.append(f"--port={port_str}")
    elif arg in ("$PORT", "${PORT}"):
        new_argv.append(port_str)
    else:
        new_argv.append(arg)

# Guard against uvicorn supervisor killing workers during PyTorch model loading
if not has_healthcheck_timeout and len(new_argv) > 1 and not any(a in ("--help", "-h", "--version", "-v") for a in new_argv):
    new_argv.extend(["--timeout-worker-healthcheck", "30"])

sys.argv = new_argv

if __name__ == "__main__":
    sys.exit(uvicorn.main.main())
