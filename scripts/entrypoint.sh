#!/bin/sh
set -e

# Fallback PORT to 8000 if unset or not a valid integer
case "$PORT" in
    ''|*[!0-9]*) PORT=8000 ;;
    *) ;;
esac

# If no arguments provided, default to python -m src.api.main
if [ $# -eq 0 ]; then
    exec python -m src.api.main
fi

# Sanitize arguments: replace literal '$PORT' or '${PORT}' with the integer value of $PORT
CMD_ARGS=""
for arg in "$@"; do
    case "$arg" in
        '$PORT'|'${PORT}')
            CMD_ARGS="$CMD_ARGS $PORT"
            ;;
        *)
            CMD_ARGS="$CMD_ARGS $arg"
            ;;
    esac
done

exec $CMD_ARGS
