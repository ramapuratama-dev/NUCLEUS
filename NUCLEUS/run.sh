#!/usr/bin/env bash
#
# run.sh — launch the NUCLEUS Streamlit dashboard.
#
# Usage:
#   ./run.sh              # set up (if needed) and run the app
#   ./run.sh --setup      # only create the venv and install dependencies
#   ./run.sh --test       # run the test suite
#   PORT=8600 ./run.sh    # run on a custom port (default 8501)
#
# The script creates a local virtual environment in .venv on first run,
# installs the pinned dependencies, then starts Streamlit from that venv — so
# you never need `streamlit` on your global PATH.

set -euo pipefail

# Always operate from the directory this script lives in.
cd "$(dirname "$0")"

VENV_DIR=".venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PORT="${PORT:-8501}"

# Pick the venv's python/streamlit paths (handle Windows Git-Bash layout too).
if [ -x "$VENV_DIR/bin/python" ]; then
  VENV_PY="$VENV_DIR/bin/python"
elif [ -x "$VENV_DIR/Scripts/python.exe" ]; then
  VENV_PY="$VENV_DIR/Scripts/python.exe"
else
  VENV_PY=""
fi

setup() {
  if [ -z "$VENV_PY" ]; then
    echo "➤ Creating virtual environment in $VENV_DIR ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    VENV_PY="$VENV_DIR/bin/python"
  fi
  echo "➤ Upgrading pip and installing dependencies ..."
  "$VENV_PY" -m pip install --quiet --upgrade pip
  "$VENV_PY" -m pip install --quiet -r requirements.txt
  echo "✓ Environment ready."
}

ensure_ready() {
  # (Re)create the venv or install deps if streamlit isn't importable yet.
  if [ -z "$VENV_PY" ] || ! "$VENV_PY" -c "import streamlit" >/dev/null 2>&1; then
    setup
  fi
}

case "${1:-}" in
  --setup)
    setup
    ;;
  --test)
    ensure_ready
    echo "➤ Running tests ..."
    "$VENV_PY" -m pytest -q
    ;;
  "")
    ensure_ready
    echo "➤ Starting NUCLEUS on http://localhost:$PORT  (Ctrl+C to stop)"
    exec "$VENV_PY" -m streamlit run app.py --server.port "$PORT"
    ;;
  *)
    echo "Unknown option: $1"
    echo "Usage: ./run.sh [--setup | --test]   (set PORT=NNNN to change port)"
    exit 1
    ;;
esac
