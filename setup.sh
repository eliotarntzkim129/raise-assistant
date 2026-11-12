#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

find_python() {
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        printf '%s' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON="$(find_python || true)"
if [[ -z "$PYTHON" ]]; then
  echo "RAISE Assistant needs Python 3.10 or newer."
  echo "Install Python 3.11 from https://www.python.org/downloads/ and run this script again."
  exit 1
fi

echo "Using $($PYTHON --version)"
if [[ ! -d .venv ]]; then
  "$PYTHON" -m venv .venv
fi

if ! .venv/bin/python -m pip install -e .; then
  echo "Package installation failed. Ask your IT team for access to an approved Python package index (PIP_INDEX_URL), then rerun bash setup.sh." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 600 .env 2>/dev/null || true
fi

if [[ "${1:-}" != "--non-interactive" && -t 0 ]]; then
  .venv/bin/python scripts/configure.py
fi

mkdir -p data/uploads exports knowledge/private
echo
echo "Setup complete. Start the app with: ./run.sh"
echo "For a configuration check, run: ./doctor.sh"

