# RDF Bundle Manifest

This bundle consolidates:

- `rdf_root_bundle_with_queries` (canonical baseline: namespaces, core ontology, SHACL, query pack)
- `coherence_ops_rdf_module_v0.1` (add-ons: SharePoint→RDF mapping, pipeline contracts, diagrams, toy data, legacy SPARQL)

## Canonical files
- Ontology: `rdf/ontology/coherence_ops_core.ttl`
- SHACL: `rdf/shapes/coherence_ops_core.shacl.ttl`
- Namespaces: `rdf/namespaces.ttl`
- Queries: `rdf/queries/*.rq`

## Add-ons (kept for reference)
- Extended ontology: `rdf/ontology/coherence_ops_extended.ttl`
- Extended SHACL: `rdf/shapes/coherence_ops_extended.shacl.ttl`
- Legacy namespaces: `rdf/namespaces_legacy.ttl`
- Legacy SPARQL queries: `rdf/queries/legacy_sparql/*.sparql`
- SharePoint mapping + samples: `rdf/mappings/`
- Pipeline contracts: `rdf/pipelines/`
- Diagram: `rdf/diagrams/`
