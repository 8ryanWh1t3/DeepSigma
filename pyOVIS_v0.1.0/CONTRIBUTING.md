# Contributing

1. Create a branch.
2. Install `pip install -e ".[dev]"`.
3. Run `ruff check .` and `pytest`.
4. Keep semantic discovery separate from authoritative governance.
5. Any change that can set `authoritative=true` is out of scope for pyOVIS and should be rejected.
6. Do not commit model weights, mission data, secrets, classified material, or sensitive operational data.
