from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from pathlib import Path

from rdflib import URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, SKOS

from .exceptions import SemanticCollisionError, ModuleRegistrationError
from .model import Collision, BridgeSuggestion, ConceptProposal, SemanticCandidate
from .registry import SemanticRegistry
from .similarity import term_similarity
from .util import normalize_text
from .validation import validate_fabric


class SemanticFabric:
    def __init__(self, name: str = "deep-sigma", registry_path: str | Path = ":memory:"):
        self.name = name
        self.registry = SemanticRegistry(registry_path)
        self.modules: dict[str, object] = {}

    def register(self, module, persist: bool = True) -> None:
        module_id = module.manifest.module_id
        if module_id in self.modules and self.modules[module_id].fingerprint != module.fingerprint:
            # Registration is version-aware but does not silently overwrite in-memory semantic state.
            raise ModuleRegistrationError(f"Module '{module_id}' already registered with a different fingerprint.")
        self.modules[module_id] = module
        if persist:
            self.registry.register(module)

    def all_terms(self):
        for module in self.modules.values():
            yield from module.terms()

    def _pair_resolved(self, a, b) -> bool:
        if self.registry.bridge_status(a.uri, b.uri) == "ACCEPTED":
            return True
        # Respect explicit RDF semantic bridges already asserted in source ontologies.
        bridge_preds = {SKOS.exactMatch, SKOS.closeMatch, OWL.equivalentClass, OWL.equivalentProperty}
        for module in self.modules.values():
            for pred in bridge_preds:
                if (URIRef(a.uri), pred, URIRef(b.uri)) in module.graph or (URIRef(b.uri), pred, URIRef(a.uri)) in module.graph:
                    return True
        return False

    def detect_collisions(self) -> list[Collision]:
        groups: dict[str, list] = defaultdict(list)
        for term in self.all_terms():
            groups[normalize_text(term.label)].append(term)

        collisions: list[Collision] = []
        for label, terms in groups.items():
            unique_uris = {t.uri for t in terms}
            unique_modules = {t.module_id for t in terms}
            if not label or len(unique_uris) < 2 or len(unique_modules) < 2:
                continue
            unresolved_pairs = [(a, b) for a, b in combinations(terms, 2) if a.uri != b.uri and not self._pair_resolved(a, b)]
            if not unresolved_pairs:
                continue
            same_kind = any(set(a.kinds) & set(b.kinds) for a, b in unresolved_pairs)
            severity = "HIGH" if same_kind else "MEDIUM"
            collisions.append(
                Collision(
                    normalized_label=label,
                    terms=sorted(terms, key=lambda t: (t.module_id, t.uri)),
                    severity=severity,
                    rationale=(
                        f"'{label}' appears as distinct URIs across modules "
                        f"{', '.join(sorted(unique_modules))}. Human review required before creating another concept."
                    ),
                )
            )
        return sorted(collisions, key=lambda c: (c.severity != "HIGH", c.normalized_label))

    def discover_bridges(self, threshold: float = 0.80, limit: int | None = None) -> list[BridgeSuggestion]:
        terms = list(self.all_terms())
        suggestions: list[BridgeSuggestion] = []
        for a, b in combinations(terms, 2):
            if a.module_id == b.module_id or a.uri == b.uri:
                continue
            score, reason = term_similarity(a, b)
            if score < threshold:
                continue
            if normalize_text(a.label) == normalize_text(b.label) and set(a.kinds) & set(b.kinds):
                relation = "skos:exactMatch"
            elif score >= 0.90:
                relation = "skos:closeMatch"
            else:
                relation = "ds:reviewMatch"
            suggestions.append(
                BridgeSuggestion(
                    source_uri=a.uri, target_uri=b.uri,
                    source_module=a.module_id, target_module=b.module_id,
                    relation=relation, score=score,
                    rationale=reason,
                )
            )
        suggestions.sort(key=lambda x: (-x.score, x.source_module, x.target_module))
        return suggestions[:limit] if limit else suggestions

    def search(self, query: str, threshold: float = 0.45, limit: int = 10) -> list[SemanticCandidate]:
        from .similarity import text_similarity
        results: list[SemanticCandidate] = []
        for term in self.all_terms():
            scores = [text_similarity(query, label) for label in term.all_labels()]
            score = max(scores) if scores else 0.0
            if score >= threshold:
                results.append(
                    SemanticCandidate(
                        uri=term.uri, module_id=term.module_id, label=term.label,
                        kinds=term.kinds, score=round(score, 4),
                        reason="label/alias similarity", definition=term.definition,
                    )
                )
        return sorted(results, key=lambda x: (-x.score, x.label))[:limit]

    def propose_concept(self, target_module: str, label: str, kind: str = "Class") -> ConceptProposal:
        if target_module not in self.modules:
            raise KeyError(f"Target module '{target_module}' is not registered.")
        candidates = self.search(label, threshold=0.50, limit=12)
        external = [c for c in candidates if c.module_id != target_module]
        exact = [c for c in candidates if normalize_text(c.label) == normalize_text(label)]
        exact_external = [c for c in exact if c.module_id != target_module]

        if exact_external:
            action = "REUSE"
            rationale = "An existing enterprise term has the same normalized label. Reuse or explicitly bridge it before creating a new URI."
        elif external and external[0].score >= 0.90:
            action = "LINK"
            rationale = "A high-similarity concept already exists in another module. Review an explicit semantic bridge before creating a local term."
        elif external and external[0].score >= 0.75:
            action = "SPECIALIZE"
            rationale = "Related enterprise meaning exists. Prefer a governed specialization/subclass if the local concept is genuinely narrower."
        elif external:
            action = "REVIEW"
            rationale = "Possible semantic neighborhood found; review before creation."
        else:
            action = "CREATE"
            rationale = "No material semantic overlap was detected in the currently registered fabric."

        return ConceptProposal(label, kind, target_module, action, candidates, rationale)

    def add_concept(
        self,
        target_module: str,
        uri: str,
        label: str,
        kind: str = "Class",
        mode: str = "CHECK_FIRST",
        approved_action: str | None = None,
    ) -> ConceptProposal:
        proposal = self.propose_concept(target_module, label, kind)
        blocked = proposal.recommended_action != "CREATE"
        if mode == "CHECK_FIRST" and blocked and approved_action is None:
            raise SemanticCollisionError(
                f"Creation blocked: {proposal.recommended_action}. {proposal.rationale}"
            )
        if blocked and approved_action not in {"REUSE", "LINK", "SPECIALIZE", "CREATE_LOCAL_OVERRIDE"}:
            raise SemanticCollisionError("An explicit human-approved action is required for overlapping enterprise meaning.")
        if approved_action in {"REUSE", "LINK"}:
            return proposal

        module = self.modules[target_module]
        rdf_type = {
            "Class": OWL.Class,
            "ObjectProperty": OWL.ObjectProperty,
            "DatatypeProperty": OWL.DatatypeProperty,
            "NamedIndividual": OWL.NamedIndividual,
            "Concept": SKOS.Concept,
        }.get(kind)
        if rdf_type is None:
            raise ValueError(f"Unsupported kind: {kind}")
        subject = URIRef(uri)
        module.graph.add((subject, RDF.type, rdf_type))
        module.graph.add((subject, RDFS.label, Literal(label)))
        module._terms = None
        from .util import graph_fingerprint
        module.fingerprint = graph_fingerprint(module.graph)
        self.registry.register(module)
        return proposal

    def accept_bridge(self, bridge: BridgeSuggestion, materialize: bool = False) -> None:
        bridge.status = "ACCEPTED"
        self.registry.save_bridge(bridge)
        if materialize and bridge.source_module in self.modules:
            pred = {
                "skos:exactMatch": SKOS.exactMatch,
                "skos:closeMatch": SKOS.closeMatch,
                "owl:equivalentClass": OWL.equivalentClass,
                "owl:equivalentProperty": OWL.equivalentProperty,
            }.get(bridge.relation)
            if pred is not None:
                module = self.modules[bridge.source_module]
                module.graph.add((URIRef(bridge.source_uri), pred, URIRef(bridge.target_uri)))
                module._terms = None
                from .util import graph_fingerprint
                module.fingerprint = graph_fingerprint(module.graph)
                self.registry.register(module)

    def validate(self):
        return validate_fabric(self)

    def close(self) -> None:
        self.registry.close()

    def __del__(self):
        try:
            self.registry.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
