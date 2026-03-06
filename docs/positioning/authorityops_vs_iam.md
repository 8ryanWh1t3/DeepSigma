# AuthorityOps vs. IAM

## The Questions They Ask

**IAM asks:**
> Can user X access resource Y?

Binary. Static. Evaluated once at the gate. The answer is yes or no.

**AuthorityOps asks:**
> Can actor X perform action Y on resource Z, given reasoning R, with non-expired assumptions, within blast radius limits, and with a complete decision lineage?

Graduated. Dynamic. Reasoning-bound. The answer is one of six verdicts, and every evaluation is sealed.

## Dimension Comparison

| Dimension | IAM | AuthorityOps |
|-----------|-----|--------------|
| **Scope** | User-to-resource permission | Actor-to-action-to-resource authority with reasoning chain |
| **Actors** | Users, groups, service accounts | Agents, humans, systems, services -- with delegation chains |
| **Reasoning** | None. Permission exists or it does not. | Required. A DLR with claims and evidence must back every decision. |
| **Time awareness** | Expiry is optional, typically coarse-grained (token TTL) | First-class. Assumptions have half-lives. Delegations have expiry. Authority decays. |
| **Blast radius** | Not modeled | Scoped by tier (tiny, small, medium, large) with policy-enforced maximums |
| **Audit** | Log who accessed what | Sealed, hash-chained audit record with assumption snapshot, expiry state, and provenance |
| **Verdict granularity** | Allow / Deny | ALLOW, BLOCK, ESCALATE, EXPIRED, MISSING_REASONING, KILL_SWITCH_ACTIVE |
| **Evaluation model** | Single gate check | 11-step pipeline with short-circuit on critical failure |
| **Kill switch** | Not built in | System-wide halt of all autonomous actions, checked every evaluation |
| **Decision reconstruction** | Requires log aggregation and inference | Every verdict is self-contained: actor, action, resource, policy, reasoning, assumptions, outcome |

## What IAM Cannot Do

### 1. Require reasoning before granting access

IAM grants access based on identity and policy. It does not ask whether the requester has thought about why they need access, whether their reasoning is backed by evidence, or whether the assumptions behind their request are still valid.

AuthorityOps requires a Decision Log Record. No DLR, no ALLOW.

### 2. Expire authority based on assumption freshness

IAM tokens expire on a clock. The underlying assumptions that justified the access grant are not tracked.

AuthorityOps tracks claim half-lives. An assumption that was valid 24 hours ago may have decayed. When it does, the verdict shifts from ALLOW to EXPIRED. The authority is not revoked -- it is recognized as stale.

### 3. Scope blast radius per action

IAM grants broad permissions: read, write, admin. It does not model the potential damage of a specific action on a specific resource.

AuthorityOps evaluates blast radius tier (tiny, small, medium, large) against a policy maximum. An agent with write access to a database cannot execute a schema migration if the blast radius exceeds its tier limit. The verdict is ESCALATE, not ALLOW.

### 4. Produce self-contained decision proofs

IAM logs record that access occurred. Reconstructing why it was granted requires joining logs across multiple systems and inferring intent.

AuthorityOps audit records are self-contained. Each record includes: the actor, the action, the resource, the policy evaluated, the reasoning reference, the assumption snapshot at evaluation time, the expiry state, and the verdict. The record is hash-chained. The chain is verifiable.

### 5. Enforce delegation chain integrity

IAM supports role assumption and cross-account access, but does not validate the full chain of delegated authority from the original grant to the acting agent.

AuthorityOps validates delegation chains: connectivity (each hop links correctly), depth limits (chains cannot exceed maximum hops), expiry (each delegation in the chain must be non-expired), and revocation (any revoked link breaks the chain).

### 6. Halt all autonomous action with a single switch

IAM has no concept of a system-wide emergency stop. Revoking access requires updating policies or rotating credentials.

AuthorityOps checks the kill switch on every evaluation. When active, every action receives KILL_SWITCH_ACTIVE regardless of authority. When cleared, normal evaluation resumes.

## When You Still Need IAM

AuthorityOps does not replace IAM. IAM handles:

- Network-level authentication (who is this request from?)
- Service mesh identity (mTLS, SPIFFE)
- Token issuance and refresh
- Coarse-grained resource permissions at the infrastructure layer

AuthorityOps operates above IAM. IAM answers "is this a valid, authenticated request?" AuthorityOps answers "should this action proceed, given everything we know about authority, reasoning, assumptions, and blast radius?"

They are complementary layers. IAM is the gate. AuthorityOps is the governance.
