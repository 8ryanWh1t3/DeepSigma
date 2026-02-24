# IRIS Query Pack — Game Studio Lattice

Deterministic query recipes for the Game Studio Lattice example. Each query
demonstrates a different IRIS resolution type against the game studio episodes
and drift signals.

---

## WHY — Episode 1 (Rating envelope breach)

```bash
python -m core iris query --type WHY --target ep-gs-001
```

**Expected (summary):**

- Tokyo approved dismemberment VFX for RONIN "The Iron Garden" DLC
- Bucharest classifier flags PEGI18/CEROZ risk — breaches current PEGI16 envelope
- Contradiction across CRE-001, REG-001, PLT-001 (3 Tier 0 claims)
- Credibility Index dropped 83 -> 64 (Structural degradation)
- Recommended patch options A/B/C with DRI escalation (red + Tier 0)
- Selected: Option C — ship DLC without dismemberment, patch later

---

## WHY — Episode 2 (Founder's Cache contradiction)

```bash
python -m core iris query --type WHY --target ep-gs-002
```

**Expected:**

- MON-001 violated by paid random rewards in restricted regions
- CRE narrative contradiction ("player-first" vs gacha mechanic)
- REG restrictions triggered (Belgium/NL lootbox prohibition; JP/KR disclosures)
- Three-way cascade loop: MON -> REG -> CRE -> MON
- Credibility Index dropped 76 -> 52 (Structural degradation)

---

## WHAT_DRIFTED — Full inventory

```bash
python -m core iris query --type WHAT_DRIFTED --json
```

**Expected:**

- ds-gs-001 (rating-mismatch) — RED, CRE/REG/PLT
- ds-gs-002 (monetization-contradiction) — RED, MON/REG/CRE
- ds-gs-003 (infrastructure-cascade) — RED, OPS/PLT/DAT/MON
- ds-gs-004 (timezone-regression) — YELLOW, OPS/PLT
- `shared-infrastructure` correlation group elevated as concentration risk
- TTL pressure + quorum thin-margin highlights for PLT-001c, REG-002d

---

## SHOW — Blast radius (shared infrastructure)

```bash
python -m core iris query --type SHOW --target shared-infrastructure
```

**Expected:**

- S003 + S023 dependency map
- "50 evidence nodes at risk" callout
- Domains impacted: PLT, OPS, CRE, MON, DAT (4 of 6)
- See: `diagrams/shared-infra-blast-radius.mmd`

---

## STATUS — Current lattice health

```bash
python -m core iris query --type STATUS
```

**Expected:**

- Baseline: ~83 / B (Minor drift)
- Active drift: 4 signals (3 red, 1 yellow)
- Dominant risk: shared-infrastructure correlation (50 nodes)
- Thin-margin claims: PLT-001c (Nintendo Lotcheck), REG-002d (KR age-gate)
