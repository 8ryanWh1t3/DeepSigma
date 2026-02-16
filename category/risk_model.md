# Risk Model: Decision Entropy and Drift Economics

> **What:** A conceptual model for how institutional decision quality decays over time.
>
> **So What:** Without this model, organizations cannot reason about when to invest in decision infrastructure — and they consistently invest too late.

---

## Concept 1: Decision Entropy

Every institution is a decision-making system. Like any system, it tends toward disorder without active maintenance.

**Decision entropy** is the measure of how much institutional reasoning has become unrecoverable, contradictory, or stale. It increases monotonically unless a mechanism exists to seal, verify, and correct decisions.

**Without Coherence Ops:** Entropy is invisible. It manifests as "nobody knows why we did this," "we debated this last quarter too," and "the policy says X but everyone does Y."

**With Coherence Ops:** Entropy is measurable. The coherence score (0–100) quantifies it across four dimensions: DLR coverage, RS completeness, DS resolution, and MG connectivity. Governance teams can track entropy trends and intervene before thresholds are breached.

---

## Concept 2: Assumption Half-Life

Every sealed decision contains assumptions — about market conditions, technical constraints, regulatory requirements, organizational capacity. These assumptions have a **half-life**: the time after which there is a 50% probability that the assumption no longer holds.

Some assumptions decay fast (pricing data, competitor positioning). Others decay slowly (legal frameworks, physical infrastructure). None are permanent.

**Without Coherence Ops:** Assumption half-life is untracked. Decisions are treated as permanently valid until a failure forces reassessment.

**With Coherence Ops:** The Drift → Patch loop monitors sealed assumptions against current state. When an assumption crosses its tolerance threshold, a drift event fires. The organization patches the decision before the stale assumption causes downstream failures.

**Key insight:** The cost of patching a drifted decision increases with time. Early drift detection (high-frequency monitoring, low-tolerance thresholds) is structurally cheaper than late detection (incident-driven, post-failure).

---

## Concept 3: Drift Accumulation Curve

Drift does not accumulate linearly. It compounds.

A single drifted decision is a local problem. But decisions depend on other decisions. When a foundational decision drifts, every downstream decision that assumed its validity is now also suspect. The number of potentially corrupted decisions grows with the depth and breadth of the dependency graph.

```
Drift cost over time (conceptual):

Cost │
     │                                    ╱
     │                                 ╱╱
     │                              ╱╱
     │                           ╱╱
     │                        ╱╱
     │                     ╱╱╱
     │                  ╱╱╱
     │              ╱╱╱╱
     │          ╱╱╱╱╱
     │     ╱╱╱╱╱╱╱
     │╱╱╱╱╱╱╱╱╱╱╱╱
     └───────────────────────────────────────
       Drift detected     Drift detected     Drift detected
       immediately        after 3 months     after incident
```

**Without Coherence Ops:** Organizations operate on the right side of this curve. Drift is detected reactively, after incidents. Remediation is expensive and incomplete.

**With Coherence Ops:** Organizations operate on the left side. Drift is detected at the point of deviation. Remediation is a patch operation, not a crisis response.

---

## Concept 4: Governance Load Multiplier

Governance overhead is a function of two variables: the **volume of decisions** requiring oversight, and the **recoverability of reasoning** behind those decisions.

When reasoning is unstructured (emails, meetings, tribal knowledge), governance requires manual reconstruction for every audit, review, or incident. The labor cost grows linearly with decision volume.

When reasoning is structured (DLR + RS + MG), governance can query the decision record directly. The marginal cost of auditing one additional decision approaches zero.

**Without Coherence Ops:** Governance cost = f(decision volume) × reconstruction overhead. This scales poorly. Organizations either slow down (more gates, more approvals) or accept risk (less oversight, wider gaps).

**With Coherence Ops:** Governance cost = f(decision volume) × query cost. Query cost is near-constant. Governance scales with decision velocity instead of against it.

---

## Concept 5: AI Amplification Risk

AI does not create new categories of decision risk. It amplifies existing ones.

**Velocity amplification:** AI agents can generate, evaluate, and execute decisions 10–100x faster than humans. If the governance layer cannot keep pace, the gap between decisions-made and decisions-auditable widens exponentially.

**Opacity amplification:** AI reasoning is often less transparent than human reasoning. Without structured capture at the point of decision, the reasoning behind AI-assisted choices is lost immediately — not gradually.

**Dependency amplification:** AI decisions often chain — one agent’s output becomes another agent’s input. A drifted assumption in an upstream decision propagates through the chain faster than any human review process can catch it.

**Without Coherence Ops:** AI amplifies decision entropy, shortens assumption half-life, accelerates drift accumulation, and increases governance load — simultaneously.

**With Coherence Ops:** AI decisions flow through the same sealed pipeline as human decisions. The governance layer scales with the decision layer because it is structural, not procedural.

---

## The Investment Calculus

Decision infrastructure is a bet on organizational longevity. The return is not immediate — it compounds:

**Year 1:** Decision records exist. Audits are faster. Onboarding is cheaper.

**Year 2:** Memory Graph has depth. Institutional recall works. Drift detection prevents a class of incidents that previously recurred.

**Year 3+:** The organization can answer questions about its own reasoning that no other organization in its industry can. This is a durable competitive advantage.

The cost of adding decision infrastructure increases with time (more unstructured decisions to backfill, more drift to remediate, more amnesia to recover from). The cost of operating without it also increases with time. The optimal moment to begin is the earliest possible one.

---

*Conceptual models only. No proprietary data or market statistics. See [category/economic_tension.md](economic_tension.md) for the failure-mode language and [category/boardroom_brief.md](boardroom_brief.md) for the executive summary.*
