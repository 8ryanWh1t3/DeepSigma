---
title: "Risk Model — Decision Entropy and Drift Economics"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# Risk Model: Decision Entropy and Drift Economics

**What:** A conceptual model for how institutional decision quality decays over time.
**So What:** Without this model, organizations cannot reason about when to invest in decision infrastructure — and they consistently invest too late.

---

## 1. Decision Entropy

Every institution is a decision-making system. Like any system, it tends toward disorder without active maintenance.

**Decision entropy** = how much institutional reasoning has become unrecoverable, contradictory, or stale. It increases monotonically unless a mechanism exists to seal, verify, and correct decisions.

- **Without Coherence Ops:** Entropy is invisible. Manifests as "nobody knows why we did this" and "we debated this last quarter too."
- **With Coherence Ops:** Entropy is measurable. The coherence score (0–100) quantifies it across DLR coverage, RS completeness, DS resolution, and MG connectivity. Governance tracks trends and intervenes before thresholds breach.

---

## 2. Assumption Half-Life

Every sealed decision contains assumptions — about market conditions, technical constraints, regulatory requirements, organizational capacity. Each has a **half-life**: the time after which there is a 50% probability the assumption no longer holds.

- Some decay fast (pricing data, competitor positioning).
- Some decay slowly (legal frameworks, physical infrastructure).
- None are permanent.

**Without Coherence Ops:** Half-life is untracked. Decisions are treated as permanently valid until failure forces reassessment.

**With Coherence Ops:** The Drift → Patch loop monitors sealed assumptions against current state. When an assumption crosses its tolerance threshold, a drift event fires. The organization patches before the stale assumption causes downstream failures.

**Key insight:** Patch cost increases with time. Early drift detection is structurally cheaper than incident-driven detection.

---

## 3. Drift Accumulation Curve

Drift compounds. A single drifted decision is local. But decisions depend on other decisions. When a foundational decision drifts, every downstream decision that assumed its validity is now suspect. Corrupted decisions grow with the depth and breadth of the dependency graph.

```
Cost
│
│                           ╱
│                         ╱╱
│                       ╱╱
│                     ╱╱
│                   ╱╱
│                 ╱╱╱
│               ╱╱╱
│             ╱╱╱╱
│           ╱╱╱╱╱
│         ╱╱╱╱╱╱╱
│╱╱╱╱╱╱╱╱╱╱╱╱
└───────────────────────────────────────
  Drift detected      Detected        Detected
  immediately         after 3 months  after incident
```

- **Without Coherence Ops:** Organizations operate on the right side. Drift detected reactively, after incidents. Remediation is expensive and incomplete.
- **With Coherence Ops:** Organizations operate on the left side. Drift detected at deviation. Remediation is a patch, not a crisis.

---

## 4. Governance Load Multiplier

Governance overhead = decision volume × reasoning recoverability.

- **Unstructured reasoning** (emails, meetings, tribal knowledge): every audit requires manual reconstruction. Labor cost grows linearly with decision volume.
- **Structured reasoning** (DLR + RS + MG): governance queries the decision record directly. Marginal cost of auditing one additional decision approaches zero.

**Without Coherence Ops:** Governance cost = volume × reconstruction overhead. Organizations either slow down (more gates) or accept risk (less oversight).

**With Coherence Ops:** Governance cost = volume × query cost. Query cost is near-constant. Governance scales with decision velocity instead of against it.

---

## 5. AI Amplification Risk

AI does not create new categories of decision risk. It amplifies existing ones:

- **Velocity amplification.** AI generates decisions 10–100× faster than humans. If governance cannot keep pace, the gap between decisions-made and decisions-auditable widens exponentially.
- **Opacity amplification.** AI reasoning is less transparent than human reasoning. Without structured capture at the point of decision, AI-assisted reasoning is lost immediately — not gradually.
- **Dependency amplification.** AI decisions chain — one agent's output becomes another's input. A drifted upstream assumption propagates faster than any human review process can catch.

**Without Coherence Ops:** AI amplifies decision entropy, shortens assumption half-life, accelerates drift accumulation, and increases governance load — simultaneously.

**With Coherence Ops:** AI decisions flow through the same sealed pipeline as human decisions. Governance scales because it is structural, not procedural.

---

## The Investment Calculus

Decision infrastructure is a bet on organizational longevity. The return compounds:

- **Year 1:** Decision records exist. Audits are faster. Onboarding is cheaper.
- **Year 2:** Memory Graph has depth. Institutional recall works. Drift detection prevents a class of recurring incidents.
- **Year 3+:** The organization can answer questions about its own reasoning that no peer can. Durable competitive advantage.

The cost of adding decision infrastructure increases with time (more unstructured decisions to backfill, more drift to remediate). The cost of operating without it also increases. The optimal moment to begin is now.

---

*Conceptual models only. No proprietary data or market statistics.*
*See [economic_tension.md](economic_tension.md) for failure-mode language and [boardroom_brief.md](boardroom_brief.md) for the executive summary.*
