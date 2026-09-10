#!/usr/bin/env bash
# Simple runner for the Graph Agent skeleton (stdlib-only, no install required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python 3 not found" >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  set -- "Who can help with injuries?"
fi

exec "$PY" -m graph_agent "$@"
