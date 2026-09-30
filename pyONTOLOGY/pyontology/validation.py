from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .model import ValidationFinding, ValidationReport
from .util import normalize_text


def validate_module(module, require_labels: bool = True) -> ValidationReport:
    report = ValidationReport()
    m = module.manifest
    if not m.module_id:
        report.findings.append(ValidationFinding("ERROR", "MODULE_ID_MISSING", "Module ID is required."))
    if not m.version:
        report.findings.append(ValidationFinding("WARNING", "VERSION_MISSING", "Ontology version is not declared.", m.module_id))
    if not m.namespace:
        report.findings.append(ValidationFinding("WARNING", "NAMESPACE_MISSING", "Primary namespace could not be inferred.", m.module_id))

    labels: dict[str, list[str]] = defaultdict(list)
    for term in module.terms():
        if require_labels and not term.label:
            report.findings.append(ValidationFinding("WARNING", "LABEL_MISSING", "Term has no label.", m.module_id, term.uri))
        labels[normalize_text(term.label)].append(term.uri)

    for label, uris in labels.items():
        if label and len(set(uris)) > 1:
            report.findings.append(
                ValidationFinding("WARNING", "INTERNAL_LABEL_COLLISION", f"Multiple URIs share label '{label}': {len(uris)} terms.", m.module_id)
            )
    return report


def validate_fabric(fabric) -> ValidationReport:
    report = ValidationReport()
    modules = list(fabric.modules.values())
    for module in modules:
        report.extend(validate_module(module).findings)

    by_namespace: dict[str, list] = defaultdict(list)
    for module in modules:
        if module.manifest.namespace:
            by_namespace[module.manifest.namespace].append(module)

    for ns, mods in by_namespace.items():
        if len(mods) < 2:
            continue
        foundations = [m for m in mods if m.manifest.role == "foundation"]
        allowed = all(m.manifest.role == "foundation" or m.manifest.extension_of for m in mods)
        if not allowed or len(foundations) > 1:
            report.findings.append(
                ValidationFinding(
                    "ERROR", "NAMESPACE_OWNERSHIP_COLLISION",
                    f"Namespace {ns} is claimed by multiple modules without a clean foundation/extension relationship: "
                    + ", ".join(m.manifest.module_id for m in mods),
                )
            )

    registered = set(fabric.modules)
    for module in modules:
        for dep in module.manifest.dependencies:
            if dep not in registered:
                report.findings.append(
                    ValidationFinding("ERROR", "DEPENDENCY_MISSING", f"Dependency '{dep}' is not registered.", module.manifest.module_id)
                )

    for collision in fabric.detect_collisions():
        report.findings.append(
            ValidationFinding(
                "WARNING" if collision.severity != "HIGH" else "ERROR",
                "SEMANTIC_LABEL_COLLISION",
                collision.rationale,
            )
        )
    return report


def validate_shacl(data_graph, shapes_path: str | Path):
    try:
        from pyshacl import validate  # type: ignore
    except ImportError as exc:
        raise RuntimeError("SHACL validation requires optional dependency: pip install deep-sigma-pyontology[shacl]") from exc
    return validate(data_graph, shacl_graph=str(shapes_path), inference="rdfs", abort_on_first=False)
