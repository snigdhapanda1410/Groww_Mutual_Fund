#!/usr/bin/env python3
"""Uvicorn CLI wrapper that safely sanitizes raw environment variable tokens like $PORT."""

import os
import sys
import uvicorn.main

raw_port = os.environ.get("PORT", "8000")
try:
    int(raw_port)
    port_str = raw_port
except (ValueError, TypeError):
    port_str = "8000"

new_argv = []
skip_next = False
for i, arg in enumerate(sys.argv):
    if skip_next:
        skip_next = False
        continue
    if arg in ("--port", "-p") and i + 1 < len(sys.argv) and sys.argv[i + 1] in ("$PORT", "${PORT}"):
        new_argv.extend([arg, port_str])
        skip_next = True
    elif arg.startswith("--port=") and arg.split("=", 1)[1] in ("$PORT", "${PORT}"):
        new_argv.append(f"--port={port_str}")
    elif arg in ("$PORT", "${PORT}"):
        new_argv.append(port_str)
    else:
        new_argv.append(arg)

sys.argv = new_argv

if __name__ == "__main__":
    sys.exit(uvicorn.main.main())
