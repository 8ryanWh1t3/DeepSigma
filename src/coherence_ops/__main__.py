"""Compatibility entry point for `python -m coherence_ops`."""
from core.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
