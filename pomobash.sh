#!/bin/bash
# Pomobash Timer launcher script

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
"$SCRIPT_DIR/venv/bin/python3" -m src.cli "$@"
