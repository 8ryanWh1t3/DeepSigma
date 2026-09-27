PYTHON ?= python

.PHONY: install dev test lint build
install:
	$(PYTHON) -m pip install -e .

dev:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

build:
	$(PYTHON) -m build
