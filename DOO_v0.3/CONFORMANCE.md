# DOO Conformance

DOO conformance is profile-based.

## CORE
Must preserve DecisionEpisode, DecisionProblem, Decision, Actor, stable identifiers, decision time, and the episode-to-decision relationship. Decision Anatomy is part of the CORE semantic contract.

## EVIDENCE
CORE plus explicit Claim, Evidence, Assumption, Source, uncertainty/contradiction relationships when represented.

## GOVERNED
EVIDENCE plus explicit Authority and lifecycle state. A system may not claim GOVERNED conformance merely because a username exists in an audit log; the authority relationship must be semantically represented.

## REPLAY
GOVERNED plus portable memory/lineage and PROV-O-compatible provenance sufficient to reconstruct the semantic decision episode.

## Round-trip rule
A system can store DOO however it wants, but export → import must not silently alter:

- object identity,
- selected/rejected alternatives,
- claim/evidence/assumption distinctions,
- represented authority,
- lifecycle state,
- supersession lineage.

## Extension rule
Extensions may add subclasses and subproperties. They should not redefine the meaning of universal DOO terms.
