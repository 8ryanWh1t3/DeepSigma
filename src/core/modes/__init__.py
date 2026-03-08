"""Domain modes — IntelOps, FranOps, ReflectionOps, AuthorityOps, ParadoxOps, ActionOps.

Six domain modes (93 handlers, 27 cascade rules) wrapping FEEDS consumers,
validators, and state stores into a composable handler interface keyed by
Function ID.

Pipeline: IntelOps → ReOps → AuthorityOps → ActionOps → FranOps
Cross-cutting: ParadoxOps (tension detection across all domains)

Module extensions:
  ReflectionOps RE-F13→F19: Institutional Memory (precedent, fingerprint, knowledge)
  ActionOps ACTION-F13→F19: Decision Accounting (cost, value, debt, ROI)
"""

from __future__ import annotations
