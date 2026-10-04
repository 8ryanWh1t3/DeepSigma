# Acceptance standard — v0.8.2 candidate

A release candidate may lock only when:

1. the exact 0.8.0 SHA `5ccdf80ac06e5fc9dc8a0374757add23a9e11d4bcfbd082a9d5d96f93d982902` remains preserved as negative-baseline evidence;
2. source tests pass;
3. installed-wheel tests pass from a directory without adjacent `src/`;
4. Claude's 0.8.0 regression/fail-closed probes are rerun and retained;
5. the v0.8.2 authority gates pass (immutable roster, no self-apply, post-Apply closure, external anchor, endpoint containment);
6. source ↔ wheel Python files match;
7. hash-list verification passes;
8. `RELEASE.json` remains candidate until an external lock verdict records the exact ZIP hash.

The original 0.8.0 R7 probe does not supply the new required startup roster; v0.8.2 therefore carries a roster-aware successor gate rather than weakening the authority contract to satisfy that old call shape.
