"""COG bundle SBOM export — CycloneDX 1.5 and SPDX 2.3 generators.

Converts a CogBundle into standardised software bill-of-materials formats
for compliance and audit workflows. No external dependencies — uses only
stdlib json/uuid.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from .models import CogBundle


def generate_cyclonedx_sbom(bundle: CogBundle) -> Dict[str, Any]:
    """Generate a CycloneDX 1.5 JSON SBOM from a COG bundle.

    Each artifact becomes a component with type "data".
    The proof chain is an external reference of type "attestation".
    Uses urn:uuid: for serial numbers (EDGE-hardening safe).
    """
    components = []
    for artifact in bundle.artifacts:
        comp: Dict[str, Any] = {
            "type": "data",
            "name": artifact.ref_id,
            "version": bundle.manifest.version,
            "description": f"COG artifact ({artifact.ref_type})",
            "properties": [
                {"name": "cog:refType", "value": artifact.ref_type},
            ],
        }
        if artifact.content_hash:
            comp["hashes"] = [
                {
                    "alg": "SHA-256",
                    "content": artifact.content_hash.replace("sha256:", ""),
                }
            ]
        components.append(comp)

    sbom: Dict[str, Any] = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "DeepSigma COG Adapter",
                        "version": bundle.manifest.version,
                    }
                ]
            },
            "component": {
                "type": "application",
                "name": bundle.manifest.bundle_id,
                "version": bundle.manifest.version,
                "description": bundle.manifest.description or "COG bundle",
            },
        },
        "components": components,
    }

    # Add proof chain as external reference
    if bundle.proof and bundle.proof.proof_chain:
        sbom["externalReferences"] = [
            {
                "type": "attestation",
                "comment": f"COG proof chain with {len(bundle.proof.proof_chain)} entries",
            }
        ]

    return sbom


def generate_spdx_sbom(bundle: CogBundle) -> Dict[str, Any]:
    """Generate an SPDX 2.3 JSON SBOM from a COG bundle.

    Each artifact becomes a package. Uses urn: namespace for identifiers.
    """
    packages = []
    relationships = []

    doc_id = f"SPDXRef-DOCUMENT-{bundle.manifest.bundle_id}"

    for i, artifact in enumerate(bundle.artifacts):
        pkg_id = f"SPDXRef-Package-{artifact.ref_id}"
        pkg: Dict[str, Any] = {
            "SPDXID": pkg_id,
            "name": artifact.ref_id,
            "versionInfo": bundle.manifest.version,
            "downloadLocation": "NOASSERTION",
            "description": f"COG artifact ({artifact.ref_type})",
            "primaryPackagePurpose": "DATA",
        }
        if artifact.content_hash:
            pkg["checksums"] = [
                {
                    "algorithm": "SHA256",
                    "checksumValue": artifact.content_hash.replace("sha256:", ""),
                }
            ]
        packages.append(pkg)
        relationships.append({
            "spdxElementId": doc_id,
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": pkg_id,
        })

    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": doc_id,
        "name": bundle.manifest.bundle_id,
        "documentNamespace": f"urn:spdx:deepsigma:{bundle.manifest.bundle_id}-{uuid.uuid4()}",
        "creationInfo": {
            "created": datetime.now(timezone.utc).isoformat(),
            "creators": ["Tool: DeepSigma COG Adapter"],
        },
        "packages": packages,
        "relationships": relationships,
    }
