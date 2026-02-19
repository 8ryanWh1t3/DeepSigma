---
title: "Game Studio Lattice — One-Screen Demo Script"
audience: Studio Exec Meeting
duration: ~5 minutes
---

# Demo Script: Game Studio Lattice

> **Setup:** Terminal open at repo root. One screen visible. No slides.

---

## Talk Track + Commands

**[0:00] Open**

> "Every AAA publisher makes thousands of cross-studio decisions a week.
> Creative, compliance, commercial. Almost none are structurally recorded.
> This is what it looks like when they are."

```bash
# Show the lattice structure
cat examples/04-game-studio-lattice/README.md | head -65
```

> "500 nodes. 4 studios. 3 titles. 6 decision domains. One franchise reputation."

---

**[0:45] Score the baseline**

> "This is the credibility index. Think of it as a credit score for institutional decisions."

```bash
python -m coherence_ops score ./examples/04-game-studio-lattice/episodes/ --json
```

> "83 out of 100. Grade B. The institution is functional but has blind spots."

---

**[1:15] Break something**

> "Tokyo approves dismemberment VFX for RONIN DLC. Bucharest QA flags it —
> that breaks the PEGI 16 rating the marketing team already promised to retailers."

```bash
python -m coherence_ops iris query --type WHY --target ep-gs-001
```

> "Three Tier 0 claims degraded across three domains. The system caught it in 2.5 hours.
> Without this? Months. Maybe never."

---

**[2:00] Show the cascade**

> "It gets worse. There's a monetization contradiction, an infrastructure single point
> of failure, and a timezone regression — all in the same 24 hours."

```bash
python -m coherence_ops iris query --type WHAT_DRIFTED --json
```

> "Four drift signals. Three red. The shared build pipeline feeds 50 evidence nodes
> across 4 domains — 18% of the entire lattice through one pipe."

---

**[2:45] Run the full cycle**

> "Here's the complete drift-to-patch loop. Detection, root cause, options,
> decision, patch, closure conditions."

```bash
python -m coherence_ops.examples.drift_patch_cycle --example game-studio
```

> "Score dropped from 83 to 41 at worst. Four patches brought it back to 72.
> Every decision is sealed with an audit trail."

---

**[3:30] Validate + generate the workbook**

> "Everything is machine-readable. The JSON validates clean."

```bash
python examples/04-game-studio-lattice/tools/validate_example_json.py
```

> "And it exports to Excel — because that's where ops teams actually live."

```bash
python examples/04-game-studio-lattice/tools/generate_gamestudio_workbook.py \
  --out /tmp/GameOps_Workbook.xlsx
```

> "8 tabs. 175 rows. Balance changes, economy tuning, feature cuts, assumptions,
> drift signals, patch plans, canon rules — all cross-referenced. Drop it into
> ChatGPT or Claude and ask: 'What drifted this week?'"

---

**[4:30] Close**

> "This is not monitoring. Not observability. Not compliance.
>
> It's the operating layer that prevents the institution from lying to itself
> over time.
>
> The question isn't whether your studio has these problems.
> It's whether you detect them in hours or months."

---

## Key Numbers (for Q&A)

| Metric | Value |
|---|---|
| Baseline Credibility Index | 83 / B |
| Worst-case during scenario | 41 / Compromised |
| Drift signals detected | 4 (3 RED, 1 YELLOW) |
| Time to detection (Scenario 1) | 2.5 hours |
| Shared infra blast radius | 50 nodes / 18% of evidence |
| Patch plans generated | 4 with closure conditions |
| Total lattice nodes | ~500 |
| Studios / Titles / Domains | 4 / 3 / 6 |
