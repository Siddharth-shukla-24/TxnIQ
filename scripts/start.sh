#!/bin/sh
# Entrypoint script for the API container.
# Runs database migrations then starts the web server.
#
# Using /bin/sh (not /bin/bash) for maximum compatibility with
# Alpine Linux base images which don't include bash by default.

set -e  
# set -e: exit immediately if any command returns a non-zero exit code.
# Without this, a failed `alembic upgrade head` would be silently ignored
# and uvicorn would start with no tables in the database.

echo "=== Running database migrations ==="
alembic upgrade head

echo "=== Migrations complete. Starting API server ==="

# exec replaces this shell process with uvicorn.
# Without exec, the shell stays as PID 1 and uvicorn runs as a child.
# With exec, uvicorn becomes PID 1 — this matters for signal handling:
# Docker sends SIGTERM to PID 1 when stopping a container.
# If uvicorn is a child process, it never receives SIGTERM and Docker
# has to forcefully kill the container after a timeout.
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1