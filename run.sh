#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/python ]]; then
  echo "The app is not set up yet. Run ./setup.sh first."
  exit 1
fi

exec .venv/bin/python -m raise_assistant.app

