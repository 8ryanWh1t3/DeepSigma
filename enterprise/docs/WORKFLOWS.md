# Coherence Ops Pilot Workflows

## 1) Create decisions

1. Open issue using `New Decision` template.
2. Create decision file from `schemas/DLR_TEMPLATE.md` under `pilot/decisions/`.
3. Add linked assumptions under `pilot/assumptions/`.
4. Include owner and seal in the decision.

## 2) File drift

1. Open issue using `Drift Signal` template.
2. Add a drift record under `pilot/drift/` from `schemas/DRIFT_SIGNAL_TEMPLATE.md`.
3. Label severity (`COH-SEV1`, `COH-SEV2`, or `COH-SEV3`) and owner state.

## 3) Deliver patches via PR

1. Create patch file from `schemas/PATCH_TEMPLATE.md` under `pilot/patches/`.
2. Update linked decision and assumptions.
3. Open PR and complete `.github/PULL_REQUEST_TEMPLATE.md` checklist.
4. Confirm `Coherence Pilot CI` workflow and local `compute_ci.py` pass.
