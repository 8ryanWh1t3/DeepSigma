# DOO Implementation Guide

## Goal
DOO is a semantic interchange model, not a mandatory database technology. A system is conformant when it preserves the meaning and identity of the DOO objects and relationships required by its declared profile.

## Storage projections

### RDF / OWL
Use classes and properties directly. Import only modules required by the deployment.

### Property graph
Map classes to node labels and object properties to typed edges. Preserve ontology IRIs in schema metadata so RDF can be reconstructed without semantic loss.

### Relational
Use durable identifiers as primary keys. Represent object properties with foreign keys or relation tables. Keep ontology IRIs in a schema registry rather than hiding semantics only in column names.

### JSON / event systems
Use `doo-context.jsonld` or equivalent URI mappings. Objects/events should retain stable ID, type, version, and references.

### Documents / spreadsheets
Represent each decision object as an addressable record. Relationships must be explicit columns/links, not inferred only from layout or proximity.

### AI / agents
Agents may propose claims, options, reviews, or patches. Authority remains external and explicit. Model output alone must not create authority.

## Interoperability test
Export a governed decision from System A and import it into System B. System B should be able to answer, without proprietary knowledge of System A: what was decided, why, based on what, by whom, under what represented authority, from which alternatives, and with what lineage.
