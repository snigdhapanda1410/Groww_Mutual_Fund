#!/bin/sh
set -e

exec python /app/scripts/entrypoint.py "$@"
