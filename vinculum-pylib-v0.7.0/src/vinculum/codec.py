"""Compare declared material representations before/after a transformation.

This does not run an LLM and cannot discover every omission in unrestricted prose.
"""
from __future__ import annotations
from dataclasses import dataclass
from .core import PairStatus
from .math import UnitRegistry, _subset
from .matrix import EvaluationReport, PairGraph
from .utils import fingerprint, primitive


@dataclass(frozen=True)
class Transformation:
    id: str
    source_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    description: str = 'declared representation transformation'

    def __post_init__(self):
        for k in ('source_ids', 'target_ids'):
            object.__setattr__(self, k, tuple(getattr(self, k)))
        if not self.id or not self.source_ids or not self.target_ids:
            raise ValueError('transformation needs id, sources and targets')
        if set(self.source_ids) & set(self.target_ids):
            raise ValueError('source and target representation identities must be distinct')
        if len(set(self.source_ids)) != len(self.source_ids) or len(set(self.target_ids)) != len(self.target_ids):
            raise ValueError('duplicate transformation endpoints')


@dataclass(frozen=True)
class CodecFinding:
    kind: str
    source_id: str | None
    target_id: str | None
    pair_id: str | None
    reason: str


@dataclass(frozen=True)
class CodecReport:
    transformation_id: str
    status: str
    findings: tuple[CodecFinding, ...]
    material_source_coverage: float
    material_target_coverage: float
    graph_fingerprint: str
    limitations: str = 'Coverage is over declared material nodes, not all semantics in the original documents.'

    def to_dict(self):
        return primitive(self)


class CodecEvaluator:
    def __init__(self, units: UnitRegistry | None = None):
        self.units = units or UnitRegistry.default()

    def evaluate(self, graph: PairGraph, report: EvaluationReport, transformation: Transformation) -> CodecReport:
        if graph.structure_fingerprint() != report.contract.get('graph_structure_fingerprint'):
            raise ValueError('report does not match graph nodes/pairs/groups snapshot')
        expected = {n.id: fingerprint(n) for n in report.representations}
        if set(expected) != set(graph.nodes) or any(expected[k] != fingerprint(n) for k, n in graph.nodes.items()):
            raise ValueError('report does not match the current representation snapshot')
        ids = set(transformation.source_ids) | set(transformation.target_ids)
        if not ids <= graph.nodes.keys():
            raise ValueError('transformation references absent nodes')
        sources, targets = set(transformation.source_ids), set(transformation.target_ids)
        source_hits, target_hits, findings = set(), set(), []
        for pair in report.pairs:
            if pair.left_id in sources and pair.right_id in targets:
                source, target = graph.nodes[pair.left_id], graph.nodes[pair.right_id]
            elif pair.right_id in sources and pair.left_id in targets:
                source, target = graph.nodes[pair.right_id], graph.nodes[pair.left_id]
            else:
                continue
            source_hits.add(source.id)
            target_hits.add(target.id)
            def add(kind, reason):
                findings.append(CodecFinding(kind, source.id, target.id, pair.pair_id, reason))
            if pair.status is PairStatus.NOT_COMPARABLE:
                failed = [c.name for c in pair.checks if c.required and c.state.value == 'FAIL']
                add('SCOPE_OR_MEANING_CHANGED', 'not equivalent under the declared contract: ' + ', '.join(failed))
            elif pair.status is PairStatus.UNRESOLVED:
                add('PRESERVATION_UNRESOLVED', 'insufficient metadata or numeric meaning for a preservation claim')
            elif pair.status is PairStatus.CONFLICT:
                add('VALUE_CHANGED', 'paired source and target have disjoint numeric states')
            if pair.comparable and source.quantity and target.quantity:
                s = self.units.normalize(source.quantity, source.unit)
                t = self.units.normalize(target.quantity, target.unit)
                if _subset(t, s) and not _subset(s, t):
                    add('UNCERTAINTY_NARROWED', 'target asserts a strictly narrower range; new supporting evidence is required')
                elif _subset(s, t) and not _subset(t, s):
                    add('PRECISION_LOST', 'target broadens the source numeric range')
                elif s == t and pair.status is PairStatus.ALIGNED:
                    add('NUMERIC_CONTENT_PRESERVED', 'same admissible numeric set after exact unit conversion')
            sv, tv = source.support.assess()['strength'], target.support.assess()['strength']
            if sv is not None and sv < 1 and tv is None:
                add('SUPPORT_ANNOTATION_OMITTED', 'source support qualification has no assessed counterpart in the target')
            elif sv is not None and tv is not None and tv > sv:
                add('SUPPORT_INCREASE_REQUIRES_EVIDENCE', 'higher target support is not established by rewording alone')
        material_sources = {i for i in sources if graph.nodes[i].material}
        material_targets = {i for i in targets if graph.nodes[i].material}
        for i in sorted(material_sources - source_hits):
            findings.append(CodecFinding('MATERIAL_SOURCE_UNPAIRED', i, None, None, 'not shown to survive transformation'))
        for i in sorted(material_targets - target_hits):
            findings.append(CodecFinding('TARGET_ADDITION_UNSUPPORTED', None, i, None, 'no source pairing supplied for this added assertion'))
        adverse = [f for f in findings if f.kind not in {'NUMERIC_CONTENT_PRESERVED', 'PRESERVATION_UNRESOLVED'}]
        status = 'DISTORTION_OR_SUPPORT_GAP' if adverse else ('UNRESOLVED' if any(f.kind == 'PRESERVATION_UNRESOLVED' for f in findings) else 'PRESERVED_WITHIN_DECLARED_SCOPE')
        return CodecReport(transformation.id, status, tuple(findings),
                           len(material_sources & source_hits) / len(material_sources) if material_sources else 1.0,
                           len(material_targets & target_hits) / len(material_targets) if material_targets else 1.0,
                           report.input_fingerprint)
