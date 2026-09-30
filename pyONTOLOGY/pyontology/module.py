from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, SKOS, DCTERMS

from .model import ModuleManifest, TermRecord
from .util import graph_fingerprint, local_name, namespace_of, hash_text

TERM_TYPES = {
    OWL.Class: "Class",
    OWL.ObjectProperty: "ObjectProperty",
    OWL.DatatypeProperty: "DatatypeProperty",
    OWL.AnnotationProperty: "AnnotationProperty",
    OWL.NamedIndividual: "NamedIndividual",
    SKOS.Concept: "Concept",
}


class OntologyModule:
    def __init__(self, graph: Graph, manifest: ModuleManifest, source_path: str | None = None):
        self.graph = graph
        self.manifest = manifest
        self.source_path = source_path
        self.fingerprint = graph_fingerprint(graph)
        self._terms: list[TermRecord] | None = None

    @classmethod
    def load(
        cls,
        path: str | Path,
        manifest_path: str | Path | None = None,
        module_id: str | None = None,
        owner: str | None = None,
        authority: int | None = None,
        role: str | None = None,
        extension_of: str | None = None,
    ) -> "OntologyModule":
        path = Path(path)
        graph = Graph()
        graph.parse(path)

        manifest_data = {}
        if manifest_path:
            manifest_data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

        ontologies = list(graph.subjects(RDF.type, OWL.Ontology))
        ontology_uri = ontologies[0] if ontologies else None
        version = cls._first_text(graph, ontology_uri, OWL.versionInfo) if ontology_uri else None
        title = cls._first_text(graph, ontology_uri, DCTERMS.title) if ontology_uri else None
        description = cls._first_text(graph, ontology_uri, DCTERMS.description) if ontology_uri else None

        inferred_namespace = None
        for s in graph.subjects():
            if isinstance(s, URIRef) and ontology_uri is not None and s != ontology_uri:
                inferred_namespace = namespace_of(str(s))
                break

        manifest = ModuleManifest(
            module_id=module_id or manifest_data.get("module_id") or path.stem,
            name=manifest_data.get("name") or title or path.stem,
            version=manifest_data.get("version") or version or "0.0.0",
            namespace=manifest_data.get("namespace") or inferred_namespace,
            owner=owner if owner is not None else manifest_data.get("owner"),
            authority=authority if authority is not None else int(manifest_data.get("authority", 0)),
            role=role or manifest_data.get("role", "module"),
            extension_of=extension_of if extension_of is not None else manifest_data.get("extension_of"),
            dependencies=list(manifest_data.get("dependencies", [])),
            description=manifest_data.get("description") or description,
        )
        return cls(graph, manifest, str(path))

    @staticmethod
    def _first_text(graph: Graph, subject, predicate) -> str | None:
        if subject is None:
            return None
        for obj in graph.objects(subject, predicate):
            return str(obj)
        return None

    def terms(self) -> list[TermRecord]:
        if self._terms is not None:
            return list(self._terms)

        subjects: set[URIRef] = set()
        for rdf_type in TERM_TYPES:
            subjects.update(s for s in self.graph.subjects(RDF.type, rdf_type) if isinstance(s, URIRef))

        records: list[TermRecord] = []
        for subject in sorted(subjects, key=str):
            kinds = sorted({TERM_TYPES[o] for o in self.graph.objects(subject, RDF.type) if o in TERM_TYPES})
            labels = [str(x) for x in self.graph.objects(subject, RDFS.label)]
            pref = [str(x) for x in self.graph.objects(subject, SKOS.prefLabel)]
            alt = [str(x) for x in self.graph.objects(subject, SKOS.altLabel)]
            uri = str(subject)
            label = (pref + labels + [local_name(uri)])[0]
            definition = next((str(x) for x in self.graph.objects(subject, SKOS.definition)), None)
            comment = next((str(x) for x in self.graph.objects(subject, RDFS.comment)), None)
            fp = hash_text(uri, "|".join(kinds), label, definition or "", comment or "")
            records.append(
                TermRecord(
                    uri=uri,
                    module_id=self.manifest.module_id,
                    kinds=tuple(kinds),
                    label=label,
                    alt_labels=tuple(dict.fromkeys(alt + labels + pref)),
                    definition=definition,
                    comment=comment,
                    namespace=namespace_of(uri),
                    local_name=local_name(uri),
                    fingerprint=fp,
                )
            )
        self._terms = records
        return list(records)

    def imports(self) -> list[str]:
        return sorted(str(o) for s in self.graph.subjects(RDF.type, OWL.Ontology) for o in self.graph.objects(s, OWL.imports))

    def stats(self) -> dict[str, int | str]:
        counts: dict[str, int | str] = {"triples": len(self.graph), "fingerprint": self.fingerprint}
        for kind in TERM_TYPES.values():
            counts[kind] = sum(kind in t.kinds for t in self.terms())
        return counts
