# Silo Prevention Invariants

1. **Search before minting.** A new URI is never the first action; the enterprise semantic neighborhood is queried first.
2. **No silent equivalence.** Similarity may propose a bridge, but only human authority may accept it.
3. **Bounded ownership.** Every module declares identity, owner, version, namespace, role, dependencies, and authority metadata.
4. **Foundation/extension is explicit.** Shared namespaces are valid only through declared extension relationships.
5. **Collision is a build condition.** Unresolved same-label/different-URI collisions can fail validation/CI.
6. **Resolved overlap stays visible.** Accepted bridges are retained in the registry rather than deleting local context.
7. **No destructive harmonization.** Federation links modules; it does not flatten them into one enterprise mega-ontology.
8. **Drift is measurable.** Every graph has a canonical fingerprint and term-level diff surface.
9. **Authority is not similarity.** A higher similarity score never becomes permission to change enterprise truth.
10. **Portable semantics.** RDF/OWL/SKOS remain the interchange substrate; the registry is an index and governance surface, not proprietary semantic storage.
