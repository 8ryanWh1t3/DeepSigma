"""Turtle interoperability with explicit semantic mapping; no remote retrieval.

Native scenario export includes a lossless JSON payload plus RDF projections. Generic
RDF import requires a field map; syntax alone is not semantic determinism.
"""
from __future__ import annotations
from dataclasses import dataclass
from .core import Representation, Scope
from .lang import SemanticRegistry, measurement
from .serialization import Scenario, scenario_from_dict
from .utils import canonical_json, fingerprint, read_json

VX_IRI = 'urn:deep-sigma:vinculum:crossorder:'


def _parse(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > 25000000:
        raise ValueError('Turtle input exceeds byte limit')
    from rdflib import Graph
    try:
        return Graph().parse(data=text, format='turtle')
    except Exception as exc:
        raise ValueError(f'invalid Turtle input ({type(exc).__name__})') from exc


def to_turtle(scenario: Scenario) -> str:
    from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD
    vx, prov = Namespace(VX_IRI), Namespace('http://www.w3.org/ns/prov#')
    g = Graph()
    g.bind('vx', vx)
    g.bind('prov', prov)
    root = URIRef(VX_IRI + 'scenario')
    payload = canonical_json(scenario.to_dict())
    g.add((root, RDF.type, vx.Scenario))
    g.add((root, vx.payload, Literal(payload, datatype=RDF.JSON)))
    g.add((root, vx.fingerprint, Literal(fingerprint(scenario.to_dict()))))
    for node in scenario.graph.nodes.values():
        r = URIRef(VX_IRI + 'node:' + fingerprint(node.id))
        g.add((root, vx.representation, r))
        g.add((r, RDF.type, vx.Representation))
        g.add((r, vx.identifier, Literal(node.id)))
        g.add((r, vx.side, Literal(node.side.value)))
        g.add((r, vx.order, Literal(node.order, datatype=XSD.integer)))
        if node.entity:
            g.add((r, vx.entity, Literal(node.entity)))
        if node.concept:
            g.add((r, vx.concept, Literal(node.concept)))
        if node.unit:
            g.add((r, vx.unit, Literal(node.unit)))
        if node.quantity:
            g.add((r, vx.numericRange, Literal(canonical_json(node.quantity), datatype=RDF.JSON)))
        for src in node.source_ids:
            g.add((r, prov.wasDerivedFrom, URIRef(VX_IRI + 'source:' + fingerprint(src))))
    for spec in scenario.graph.pairs.values():
        p = URIRef(VX_IRI + 'pair:' + fingerprint(spec.id))
        g.add((root, vx.pair, p))
        g.add((p, RDF.type, vx.Pair))
        g.add((p, vx.identifier, Literal(spec.id)))
        g.add((p, vx.left, URIRef(VX_IRI + 'node:' + fingerprint(spec.left_id))))
        g.add((p, vx.right, URIRef(VX_IRI + 'node:' + fingerprint(spec.right_id))))
    return g.serialize(format='turtle')


def from_turtle(text: str) -> Scenario:
    from rdflib import Namespace, RDF
    from rdflib.compare import isomorphic
    vx = Namespace(VX_IRI)
    graph = _parse(text)
    roots = list(graph.subjects(RDF.type, vx.Scenario))
    if len(roots) != 1:
        raise ValueError('native scenario Turtle needs exactly one vx:Scenario; generic RDF needs RDFFieldMap')
    payloads = list(graph.objects(roots[0], vx.payload))
    if len(payloads) != 1:
        raise ValueError('native scenario payload missing or ambiguous')
    scenario = scenario_from_dict(read_json(str(payloads[0])))
    # Reject a modified RDF projection that disagrees with the lossless payload.
    if not isomorphic(graph, _parse(to_turtle(scenario))):
        raise ValueError('RDF projection and canonical scenario payload disagree')
    return scenario


@dataclass(frozen=True)
class RDFFieldMap:
    label_predicate: str
    value_predicate: str
    concept: str
    unit: str
    scope: Scope
    defense_predicate: str | None = None
    language_order: int = 1
    mathematics_order: int = 1


def project_turtle(text: str, mapping: RDFFieldMap, *, registry=None, graph_id='TTL', pair_unique=False):
    """Project explicitly mapped RDF labels and numeric literals into representations.

    Multiple values/labels are retained as distinct nodes and never auto-paired.
    No ontology inference, remote IRIs, SPARQL SERVICE, JSON-LD fetching or LLM calls.
    """
    from rdflib import URIRef, Literal
    from .hinge import HingePolicy
    from .math import UnitRegistry
    from .matrix import PairGraph
    registry = registry or SemanticRegistry.default()
    source = _parse(text)
    g = PairGraph(graph_id)
    lp, vp = URIRef(mapping.label_predicate), URIRef(mapping.value_predicate)
    subjects = sorted(set(source.subjects(lp, None)) | set(source.subjects(vp, None)), key=str)
    for subject in subjects:
        # BNode IDs are parser-local; no invented cross-document stable identity.
        entity = str(subject)
        if not isinstance(subject, URIRef):
            entity = None
        labels = sorted(source.objects(subject, lp), key=str)
        values = sorted(source.objects(subject, vp), key=str)
        left, right = [], []
        for i, label in enumerate(labels):
            node = registry.representation(str(label), id=f'{graph_id}:L:{len(g.nodes)}', entity=entity,
                                           concept=mapping.concept, scope=mapping.scope,
                                           order=mapping.language_order, source_ids=(f'RDF:{subject}',))
            g.add_node(node)
            left.append(node.id)
        defense = None
        if mapping.defense_predicate:
            dd = list(source.objects(subject, URIRef(mapping.defense_predicate)))
            if len(dd) == 1:
                from .utils import unit_score
                defense = unit_score(str(dd[0]), 'mapped RDF defense')
        for value in values:
            if not isinstance(value, Literal):
                quantity = None
            else:
                try:
                    from .core import NumericRange
                    quantity = NumericRange.point(str(value))
                except ValueError:
                    quantity = None
            node = measurement(id=f'{graph_id}:M:{len(g.nodes)}', entity=entity,
                               concept=mapping.concept, interval=quantity, unit=mapping.unit,
                               scope=mapping.scope, order=mapping.mathematics_order,
                               defense=defense, defense_basis='explicit RDFFieldMap; observation reliability not inferred from literal syntax',
                               source_ids=(f'RDF:{subject}',))
            g.add_node(node)
            right.append(node.id)
        if pair_unique and len(left) == len(right) == 1:
            g.add_pair(left[0], right[0], rationale='caller enabled unique same-subject RDF field pairing',
                       alignment_support=None)
    return Scenario(g, HingePolicy(), UnitRegistry.default())
