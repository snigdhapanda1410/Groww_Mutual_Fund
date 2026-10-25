#!/usr/bin/env python3
"""Universal container entrypoint for Railway / Docker deployments.

Sanitizes any command-line arguments containing unresolved environment tokens like
'$PORT' or '${PORT}', and launches the application.
"""

import os
import shlex
import subprocess
import sys


def get_port() -> str:
    """Return a validated integer port string from environment or default 8000."""
    raw_port = os.environ.get("PORT", "8000")
    try:
        int(raw_port)
        return raw_port
    except (ValueError, TypeError):
        return "8000"


def sanitize_args(raw_args: list[str], port_str: str) -> list[str]:
    """Replace unresolved $PORT or ${PORT} tokens with the validated integer port."""
    if len(raw_args) == 1 and (" " in raw_args[0] or "$PORT" in raw_args[0]):
        tokens = shlex.split(raw_args[0])
    else:
        tokens = list(raw_args)

    sanitized = []
    for token in tokens:
        if token in ("$PORT", "${PORT}"):
            sanitized.append(port_str)
        elif token.startswith("--port=") and token.split("=", 1)[1] in ("$PORT", "${PORT}"):
            sanitized.append(f"--port={port_str}")
        elif "$PORT" in token:
            sanitized.append(token.replace("$PORT", port_str))
        elif "${PORT}" in token:
            sanitized.append(token.replace("${PORT}", port_str))
        else:
            sanitized.append(token)
    return sanitized


def main():
    port = get_port()
    os.environ["PORT"] = port
    os.environ.setdefault("WEB_CONCURRENCY", "1")
    os.environ.setdefault("HF_HOME", "/app/data/cache/huggingface")
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", "/app/data/cache/sentence_transformers")
    os.environ.setdefault("NLTK_DATA", "/app/data/cache/nltk_data")

    # Default to running the FastAPI app if no arguments given
    if len(sys.argv) <= 1:
        cmd = [sys.executable, "-m", "src.api.main"]
        sys.exit(subprocess.call(cmd))

    sanitized = sanitize_args(sys.argv[1:], port)
    sys.exit(subprocess.call(sanitized))


if __name__ == "__main__":
    main()
