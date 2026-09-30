from pathlib import Path
from pyontology import Fabric, OntologyModule

HERE = Path(__file__).parent

fabric = Fabric("deep-sigma", HERE / "deep_sigma_registry.sqlite")
core = OntologyModule.load(
    HERE / "ontologies/coherence_ops_v2.ttl",
    HERE / "manifests/coherence_ops_v2.module.json",
)
lenses = OntologyModule.load(
    HERE / "ontologies/coherence_ops_lenses_v2.1.ttl",
    HERE / "manifests/coherence_ops_lenses_v2.1.module.json",
)

fabric.register(core)
fabric.register(lenses)

print("MODULES")
for module in fabric.registry.modules():
    print(f"- {module.module_id}: v{module.version} [{module.role}]")

print("\nVALIDATION")
report = fabric.validate()
print("PASS" if report.ok else "FAIL")
for finding in report.findings:
    print(f"{finding.severity}: {finding.code}: {finding.message}")

print("\nSEARCH: decision")
for hit in fabric.search("decision")[:8]:
    print(f"{hit.score:.2f}  {hit.module_id:24} {hit.label}  {hit.uri}")

print("\nCREATE GATE: Decision")
proposal = fabric.propose_concept("coherence-ops-lenses", "Decision")
print(proposal.recommended_action, "-", proposal.rationale)
for candidate in proposal.candidates[:5]:
    print(f"  {candidate.score:.2f} {candidate.module_id}: {candidate.label}")
