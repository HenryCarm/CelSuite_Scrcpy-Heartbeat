#!/usr/bin/env bash
# Launcher for Scrcpy Cloud Build & Deploy Hub
set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_VENV="/home/henry/Documents/Projects/Python/venv/bin/python"

echo "🚀 Starting Scrcpy Cloud Build & Deploy Hub..."
exec "$PYTHON_VENV" "$PROJECT_DIR/build_monitor_gui.py" "$@"
