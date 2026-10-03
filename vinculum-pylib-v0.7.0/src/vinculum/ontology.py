"""Local RDF/SKOS label resolution. Labels and similarity are not numeric facts."""
from __future__ import annotations
from dataclasses import dataclass, replace
from .core import Representation
from .rdf import _parse
from .utils import fingerprint, identifier


@dataclass(frozen=True)
class TermResolution:
    original: str | None
    canonical: str | None
    status: str
    candidates: tuple[str, ...]
    basis: str


class OntologyRegistry:
    """Unique label lookup plus explicit ID aliases; no remote imports or inference.

    SKOS broader/narrower/related and OWL sameAs are retained in source, but never
    silently converted into pair comparability. Only explicit application alias maps establish equivalent IDs.
    """
    def __init__(self, *, entity_aliases=None, concept_aliases=None):
        self.entity_aliases = dict(entity_aliases or {})
        self.concept_aliases = dict(concept_aliases or {})
        self.labels = {}
        self._triples = []
        self._source_fingerprints = []
        for mapping in (self.entity_aliases,self.concept_aliases):
            for k,v in mapping.items(): identifier(k);identifier(v)
            for key in mapping: self._canonical(key,mapping)

    @staticmethod
    def _canonical(key,mapping):
        seen=set()
        while key in mapping and mapping[key] != key:
            if key in seen: raise ValueError('cyclic ontology alias mapping')
            seen.add(key);key=mapping[key]
        return key

    @classmethod
    def from_turtle(cls, text, *, language='en', entity_aliases=None, concept_aliases=None):
        from rdflib import Literal, URIRef, RDFS, SKOS
        g=_parse(text)
        obj=cls(entity_aliases=entity_aliases,concept_aliases=concept_aliases)
        obj._source_fingerprints.append(fingerprint(text))
        for s,p,o in g:
            obj._triples.append((str(s),str(p),str(o)))
            if p in {SKOS.prefLabel,SKOS.altLabel,RDFS.label} and isinstance(s,URIRef) and isinstance(o,Literal):
                if o.language is None or o.language == language:
                    obj.labels.setdefault(str(o).strip().casefold(),set()).add(str(s))
        return obj

    def resolve(self, value, *, kind='concept', labels=False):
        if kind not in {'entity','concept'}: raise ValueError('ontology kind must be entity or concept')
        if value is None: return TermResolution(None,None,'UNRESOLVED',(),'identifier missing')
        identifier(value)
        mapping=self.entity_aliases if kind=='entity' else self.concept_aliases
        if value in mapping:
            canonical=self._canonical(value,mapping)
            return TermResolution(value,canonical,'RESOLVED',(canonical,),'explicit application alias; not fuzzy similarity')
        if kind=='concept' and labels:
            candidates=tuple(sorted({self._canonical(x,mapping) for x in self.labels.get(value.strip().casefold(),())}))
            if len(candidates)==1:
                return TermResolution(value,candidates[0],'RESOLVED',candidates,'unique language-filtered RDF/SKOS label')
            if len(candidates)>1:
                return TermResolution(value,None,'UNRESOLVED',candidates,'ambiguous label; no first-match selection')
        return TermResolution(value,value,'UNCHANGED',(value,),'retained explicit identifier; equivalence not inferred')

    def normalize(self,node: Representation, *, resolve_labels=False):
        entity=self.resolve(node.entity,kind='entity')
        concept=self.resolve(node.concept,kind='concept',labels=resolve_labels)
        return replace(node,entity=entity.canonical,concept=concept.canonical),(entity,concept)

    def fingerprint(self):
        return fingerprint({'entity_aliases':self.entity_aliases,'concept_aliases':self.concept_aliases,
                            'labels':{k:sorted(v) for k,v in self.labels.items()},'sources':self._source_fingerprints})
