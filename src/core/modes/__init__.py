"""Domain modes — IntelOps, FranOps, ReflectionOps, AuthorityOps, ParadoxOps, ActionOps.

Six domain modes (79 handlers) wrapping FEEDS consumers, validators, and
state stores into a composable handler interface keyed by Function ID.

Pipeline: IntelOps → ReOps → AuthorityOps → ActionOps → FranOps
Cross-cutting: ParadoxOps (tension detection across all domains)
"""

from __future__ import annotations
