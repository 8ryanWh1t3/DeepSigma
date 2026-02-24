"""RDF/SPARQL service for semantic lattice queries.

Serialises Coherence Ops lattice objects (Claim, DriftEvent,
CorrelationCluster) into an RDF graph using the ``ds:``
namespace, then exposes SPARQL query capabilities via rdflib.

Requires the ``rdf`` optional dependency::

    pip install 'deepsigma[rdf]'

Usage::

    from services.sparql_service import (
        LatticeGraph, SPARQLService,
    )
    from credibility_engine.models import make_default_claims

    lg = LatticeGraph()
    lg.add_claims(make_default_claims())
    svc = SPARQLService(lg)

    # Standard queries
    rows = svc.low_confidence_claims(threshold=0.7)
    ttl  = svc.export_turtle()
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
)

try:
    from rdflib import (  # noqa: F401
        Graph,
        Literal,
        Namespace,
    )
    from rdflib.namespace import OWL, RDF, XSD

    _HAS_RDFLIB = True
except ImportError:  # pragma: no cover
    _HAS_RDFLIB = False
    Namespace = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# ── Namespace ──────────────────────────────────────────

DS_URI = "https://deepsigma.ai/ns/coherence#"
DS = Namespace(DS_URI) if _HAS_RDFLIB else None  # type: ignore[arg-type]

# ── Standard SPARQL queries ────────────────────────────

Q_LOW_CONFIDENCE = """\
PREFIX ds: <https://deepsigma.ai/ns/coherence#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?claimId ?title ?confidence ?state
WHERE {{
  ?claim a ds:Claim ;
         ds:claimId ?claimId ;
         ds:title ?title ;
         ds:confidence ?confidence ;
         ds:state ?state .
  FILTER(?confidence < {threshold})
}}
ORDER BY ASC(?confidence)
"""

Q_EVIDENCE_CHAIN = """\
PREFIX ds: <https://deepsigma.ai/ns/coherence#>

SELECT ?claimId ?claimTitle ?evidenceId
       ?sourceId
WHERE {{
  ?claim a ds:Claim ;
         ds:claimId ?claimId ;
         ds:title ?claimTitle ;
         ds:hasEvidence ?ev .
  ?ev ds:evidenceId ?evidenceId .
  OPTIONAL {{ ?ev ds:usesSource ?src .
              ?src ds:sourceId ?sourceId . }}
  FILTER(?claimId = "{claim_id}")
}}
"""

Q_DRIFT_BY_SOURCE = """\
PREFIX ds: <https://deepsigma.ai/ns/coherence#>

SELECT ?driftId ?severity ?category ?region
       ?claimId
WHERE {{
  ?drift a ds:DriftEvent ;
         ds:driftId ?driftId ;
         ds:severity ?severity ;
         ds:category ?category ;
         ds:region ?region .
  OPTIONAL {{
    ?drift ds:affectsClaim ?claim .
    ?claim ds:claimId ?claimId .
  }}
  FILTER(?region = "{source_region}")
}}
ORDER BY DESC(?severity)
"""

Q_ALL_CLAIMS = """\
PREFIX ds: <https://deepsigma.ai/ns/coherence#>

SELECT ?claimId ?title ?state ?confidence
       ?region ?domain
WHERE {
  ?claim a ds:Claim ;
         ds:claimId ?claimId ;
         ds:title ?title ;
         ds:state ?state ;
         ds:region ?region ;
         ds:domain ?domain .
  OPTIONAL { ?claim ds:confidence ?confidence . }
}
ORDER BY ?claimId
"""

Q_ALL_DRIFT = """\
PREFIX ds: <https://deepsigma.ai/ns/coherence#>

SELECT ?driftId ?severity ?category ?region
       ?fingerprint
WHERE {
  ?drift a ds:DriftEvent ;
         ds:driftId ?driftId ;
         ds:severity ?severity ;
         ds:category ?category ;
         ds:region ?region ;
         ds:fingerprint ?fingerprint .
}
ORDER BY ?driftId
"""

Q_CLUSTER_RISK = """\
PREFIX ds: <https://deepsigma.ai/ns/coherence#>

SELECT ?clusterId ?label ?coefficient ?status
       ?claimsAffected
WHERE {
  ?cluster a ds:CorrelationCluster ;
           ds:clusterId ?clusterId ;
           ds:label ?label ;
           ds:coefficient ?coefficient ;
           ds:status ?status ;
           ds:claimsAffected ?claimsAffected .
}
ORDER BY DESC(?coefficient)
"""

Q_GRAPH_STATS = """\
PREFIX ds: <https://deepsigma.ai/ns/coherence#>

SELECT
  (COUNT(DISTINCT ?claim) AS ?claimCount)
  (COUNT(DISTINCT ?drift) AS ?driftCount)
  (COUNT(DISTINCT ?cluster) AS ?clusterCount)
WHERE {
  { ?claim a ds:Claim }
  UNION
  { ?drift a ds:DriftEvent }
  UNION
  { ?cluster a ds:CorrelationCluster }
}
"""


# ── QueryResult ────────────────────────────────────────


@dataclass
class QueryResult:
    """Result of a SPARQL query."""

    query_name: str
    rows: List[Dict[str, Any]]
    elapsed_ms: float = 0.0
    variables: List[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.rows)


# ── LatticeGraph ───────────────────────────────────────


class LatticeGraph:
    """In-memory RDF graph built from lattice objects.

    Converts Claim, DriftEvent, and CorrelationCluster
    Python dataclasses into RDF triples using the ``ds:``
    namespace from the Coherence Ops ontology.
    """

    def __init__(self) -> None:
        self._require_rdflib()
        self._g = Graph()
        self._g.bind("ds", DS)
        self._g.bind("owl", OWL)

    @property
    def graph(self) -> Graph:
        return self._g

    @property
    def triple_count(self) -> int:
        return len(self._g)

    # ── Bulk loaders ───────────────────────────────

    def add_claims(self, claims: Sequence[Any]) -> int:
        """Add Claim dataclass instances. Returns count."""
        added = 0
        for c in claims:
            self._add_claim(c)
            added += 1
        return added

    def add_drift_events(
        self, events: Sequence[Any],
    ) -> int:
        """Add DriftEvent instances. Returns count."""
        added = 0
        for ev in events:
            self._add_drift_event(ev)
            added += 1
        return added

    def add_clusters(
        self, clusters: Sequence[Any],
    ) -> int:
        """Add CorrelationCluster instances. Returns count."""
        added = 0
        for cl in clusters:
            self._add_cluster(cl)
            added += 1
        return added

    def link_drift_to_claim(
        self,
        drift_id: str,
        claim_id: str,
    ) -> None:
        """Add ``ds:affectsClaim`` edge."""
        drift_uri = DS[f"drift/{drift_id}"]
        claim_uri = DS[f"claim/{claim_id}"]
        self._g.add((
            drift_uri,
            DS.affectsClaim,
            claim_uri,
        ))

    def link_evidence(
        self,
        claim_id: str,
        evidence_id: str,
        source_id: Optional[str] = None,
    ) -> None:
        """Add evidence node linked to a claim."""
        claim_uri = DS[f"claim/{claim_id}"]
        ev_uri = DS[f"evidence/{evidence_id}"]
        self._g.add((ev_uri, RDF.type, DS.Evidence))
        self._g.add((
            ev_uri,
            DS.evidenceId,
            Literal(evidence_id),
        ))
        self._g.add((claim_uri, DS.hasEvidence, ev_uri))
        if source_id:
            src_uri = DS[f"source/{source_id}"]
            self._g.add((
                src_uri, RDF.type, DS.SourceArtifact,
            ))
            self._g.add((
                src_uri,
                DS.sourceId,
                Literal(source_id),
            ))
            self._g.add((ev_uri, DS.usesSource, src_uri))

    # ── Single-object serializers ──────────────────

    def _add_claim(self, claim: Any) -> None:
        uri = DS[f"claim/{claim.id}"]
        g = self._g
        g.add((uri, RDF.type, DS.Claim))
        g.add((
            uri, DS.claimId, Literal(claim.id),
        ))
        g.add((
            uri, DS.title, Literal(claim.title),
        ))
        g.add((
            uri, DS.state, Literal(claim.state),
        ))
        if claim.confidence is not None:
            g.add((
                uri,
                DS.confidence,
                Literal(
                    claim.confidence,
                    datatype=XSD.double,
                ),
            ))
        g.add((
            uri,
            DS.kRequired,
            Literal(
                claim.k_required,
                datatype=XSD.integer,
            ),
        ))
        g.add((
            uri,
            DS.nTotal,
            Literal(
                claim.n_total,
                datatype=XSD.integer,
            ),
        ))
        g.add((
            uri,
            DS.ttlRemaining,
            Literal(
                claim.ttl_remaining,
                datatype=XSD.integer,
            ),
        ))
        g.add((
            uri, DS.region, Literal(claim.region),
        ))
        g.add((
            uri, DS.domain, Literal(claim.domain),
        ))
        if claim.correlation_group:
            g.add((
                uri,
                DS.correlationGroup,
                Literal(claim.correlation_group),
            ))
        g.add((
            uri,
            DS.lastVerified,
            Literal(claim.last_verified),
        ))

    def _add_drift_event(self, ev: Any) -> None:
        uri = DS[f"drift/{ev.id}"]
        g = self._g
        g.add((uri, RDF.type, DS.DriftEvent))
        g.add((
            uri, DS.driftId, Literal(ev.id),
        ))
        g.add((
            uri, DS.severity, Literal(ev.severity),
        ))
        g.add((
            uri,
            DS.fingerprint,
            Literal(ev.fingerprint),
        ))
        g.add((
            uri,
            DS.timestamp,
            Literal(ev.timestamp),
        ))
        g.add((
            uri,
            DS.tierImpact,
            Literal(
                ev.tier_impact,
                datatype=XSD.integer,
            ),
        ))
        g.add((
            uri, DS.category, Literal(ev.category),
        ))
        g.add((
            uri, DS.region, Literal(ev.region),
        ))
        g.add((
            uri,
            DS.autoResolved,
            Literal(
                ev.auto_resolved,
                datatype=XSD.boolean,
            ),
        ))

    def _add_cluster(self, cl: Any) -> None:
        uri = DS[f"cluster/{cl.id}"]
        g = self._g
        g.add((uri, RDF.type, DS.CorrelationCluster))
        g.add((
            uri, DS.clusterId, Literal(cl.id),
        ))
        g.add((
            uri, DS.label, Literal(cl.label),
        ))
        g.add((
            uri,
            DS.coefficient,
            Literal(
                cl.coefficient,
                datatype=XSD.double,
            ),
        ))
        g.add((
            uri, DS.status, Literal(cl.status),
        ))
        g.add((
            uri,
            DS.claimsAffected,
            Literal(
                cl.claims_affected,
                datatype=XSD.integer,
            ),
        ))
        for src in cl.sources:
            g.add((
                uri, DS.hasSource, Literal(src),
            ))
        for dom in cl.domains:
            g.add((
                uri, DS.hasDomain, Literal(dom),
            ))
        for reg in cl.regions:
            g.add((
                uri,
                DS.hasRegion,
                Literal(reg),
            ))

    # ── Helpers ────────────────────────────────────

    @staticmethod
    def _require_rdflib() -> None:
        if not _HAS_RDFLIB:
            raise ImportError(
                "rdflib not installed. "
                "Install with: pip install "
                "'deepsigma[rdf]'"
            )


# ── SPARQLService ──────────────────────────────────────


class SPARQLService:
    """SPARQL query interface over a LatticeGraph.

    Wraps rdflib's SPARQL 1.1 engine for in-process
    semantic queries on the coherence lattice.

    Parameters
    ----------
    lattice : LatticeGraph
        The populated lattice graph.
    """

    def __init__(
        self, lattice: LatticeGraph,
    ) -> None:
        self._lattice = lattice
        self._query_count = 0
        self._total_ms = 0.0

    @property
    def query_count(self) -> int:
        return self._query_count

    @property
    def avg_latency_ms(self) -> float:
        if self._query_count == 0:
            return 0.0
        return self._total_ms / self._query_count

    # ── Standard queries ───────────────────────────

    def low_confidence_claims(
        self, threshold: float = 0.7,
    ) -> QueryResult:
        """Claims with confidence below threshold."""
        sparql = Q_LOW_CONFIDENCE.format(
            threshold=threshold,
        )
        return self._execute(
            "low_confidence_claims", sparql,
        )

    def evidence_chain(
        self, claim_id: str,
    ) -> QueryResult:
        """Evidence chain for a specific claim."""
        sparql = Q_EVIDENCE_CHAIN.format(
            claim_id=claim_id,
        )
        return self._execute(
            "evidence_chain", sparql,
        )

    def drift_by_source(
        self, source_region: str,
    ) -> QueryResult:
        """Drift signals correlated with a region."""
        sparql = Q_DRIFT_BY_SOURCE.format(
            source_region=source_region,
        )
        return self._execute(
            "drift_by_source", sparql,
        )

    def all_claims(self) -> QueryResult:
        """All claims in the lattice."""
        return self._execute(
            "all_claims", Q_ALL_CLAIMS,
        )

    def all_drift(self) -> QueryResult:
        """All drift events in the lattice."""
        return self._execute(
            "all_drift", Q_ALL_DRIFT,
        )

    def cluster_risk(self) -> QueryResult:
        """Correlation clusters by risk."""
        return self._execute(
            "cluster_risk", Q_CLUSTER_RISK,
        )

    def graph_stats(self) -> QueryResult:
        """Aggregate node counts."""
        return self._execute(
            "graph_stats", Q_GRAPH_STATS,
        )

    def custom_query(
        self, name: str, sparql: str,
    ) -> QueryResult:
        """Execute an arbitrary SPARQL SELECT."""
        return self._execute(name, sparql)

    # ── Export ─────────────────────────────────────

    def export_turtle(self) -> str:
        """Serialize the graph to Turtle format."""
        return self._lattice.graph.serialize(
            format="turtle",
        )

    def export_ntriples(self) -> str:
        """Serialize the graph to N-Triples."""
        return self._lattice.graph.serialize(
            format="nt",
        )

    # ── Trust Scorecard integration ────────────────

    def rdf_metrics(self) -> Dict[str, Any]:
        """Metrics for Trust Scorecard integration.

        Returns counts, query stats, and health data.
        """
        stats = self.graph_stats()
        row = stats.rows[0] if stats.rows else {}
        return {
            "triple_count": self._lattice.triple_count,
            "claim_count": int(
                row.get("claimCount", 0),
            ),
            "drift_count": int(
                row.get("driftCount", 0),
            ),
            "cluster_count": int(
                row.get("clusterCount", 0),
            ),
            "queries_executed": self._query_count,
            "avg_query_latency_ms": round(
                self.avg_latency_ms, 2,
            ),
        }

    # ── Internal ───────────────────────────────────

    def _execute(
        self, name: str, sparql: str,
    ) -> QueryResult:
        start = time.monotonic()
        g = self._lattice.graph
        results = g.query(sparql)
        elapsed = (time.monotonic() - start) * 1000

        self._query_count += 1
        self._total_ms += elapsed

        variables = [
            str(v) for v in (results.vars or [])
        ]
        rows: List[Dict[str, Any]] = []
        for row in results:
            rows.append({
                str(v): self._to_python(
                    getattr(row, str(v), None),
                )
                for v in variables
            })

        logger.debug(
            "SPARQL %s: %d rows in %.1fms",
            name, len(rows), elapsed,
        )
        return QueryResult(
            query_name=name,
            rows=rows,
            elapsed_ms=round(elapsed, 2),
            variables=variables,
        )

    @staticmethod
    def _to_python(val: Any) -> Any:
        """Convert rdflib term to a Python value."""
        if val is None:
            return None
        if hasattr(val, "toPython"):
            return val.toPython()
        return str(val)
