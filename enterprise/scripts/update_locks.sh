#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip pip-tools
mkdir -p requirements/locks

# Core and contributor install sets.
pip-compile --strip-extras pyproject.toml -o requirements/locks/base.txt
pip-compile --strip-extras pyproject.toml --extra dev --extra excel --extra local -o requirements/locks/dev-excel-local.txt

# Optional extras lockfiles.
pip-compile --strip-extras pyproject.toml --extra rdf -o requirements/locks/rdf.txt
pip-compile --strip-extras pyproject.toml --extra azure -o requirements/locks/azure.txt
pip-compile --strip-extras pyproject.toml --extra snowflake -o requirements/locks/snowflake.txt
pip-compile --strip-extras pyproject.toml --extra openclaw -o requirements/locks/openclaw.txt

# KPI workflow toolchain.
pip-compile --strip-extras requirements/locks/kpi.in -o requirements/locks/kpi.txt
pip-compile --strip-extras requirements/locks/release-build.in -o requirements/locks/release-build.txt

echo "Lockfiles updated under requirements/locks/."
