"""Domain modes — IntelOps, FranOps, ReflectionOps, AuthorityOps.

Each domain mode wraps existing FEEDS consumers, validators, and state stores
into a composable handler interface keyed by Function ID.

AuthorityOps sits at: IntelOps → ReOps → AuthorityOps → Execution → FranOps
"""

from __future__ import annotations
