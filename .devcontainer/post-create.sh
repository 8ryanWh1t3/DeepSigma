#!/usr/bin/env bash
set -euo pipefail

echo "[devcontainer] python: $(python --version)"
echo "[devcontainer] node: $(node --version)"

python -m pip install --upgrade pip
pip install -c requirements/locks/dev-excel-local.txt -e ".[dev,excel,local]" pydantic

if [ -f dashboard/package-lock.json ]; then
  npm --prefix dashboard ci
else
  npm --prefix dashboard install
fi

echo "[devcontainer] install complete"
echo "[devcontainer] try: make demo"
