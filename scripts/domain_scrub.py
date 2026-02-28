#!/usr/bin/env python3
"""
Generic Primitive Enforcement (GPE-Strict) + Tokenizer AutoFix + Ignore-Code-Blocks

Usage:
  python scripts/domain_scrub.py
  python scripts/domain_scrub.py --fix
  python scripts/domain_scrub.py --fix --paths docs examples edge src

Rules:
  - DENYLIST = hard fail anywhere (including code blocks)
  - HEURISTICS = hard fail, but ignore fenced code blocks / inline code to reduce noise
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


# ----------------------------
# Configuration
# ----------------------------

FORBIDDEN_TERMS: List[str] = [
    "ARA",
    "Applied Research Associates",
    "DoD",
    "DOD",
    "Department of Defense",
    "OPMG",
    "HQDA",
    "Pentagon",
    "NGA",
    "NSA",
    "CIA",
    "DIA",
    "AR 190",
    "AR-190",
    "DoDI",
    "CJCS",
    "SIGINT",
    "HUMINT",
    "OPSEC",
]

REPLACEMENTS: Dict[str, str] = {
    "applied research associates": "PartnerOrg",
    "ara": "PartnerOrg",
    "department of defense": "CustomerOrg",
    "dod": "CustomerOrg",
    "opmg": "ProgramOffice",
    "hqda": "PolicyOffice",
    "pentagon": "HQSite",
    "nga": "ExternalAgency",
    "nsa": "ExternalAgency",
    "cia": "ExternalAgency",
    "dia": "ExternalAgency",
    "sigint": "SignalSource",
    "humint": "HumanSource",
    "opsec": "OperationalSecurity",
    "dodi": "PolicyDirective",
    "cjcs": "PolicyDirective",
    "ar 190": "Policy-190",
    "ar-190": "Policy-190",
}

HEURISTIC_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("Likely agency/program acronym (3-6 caps)", re.compile(r"\b[A-Z]{3,6}\b")),
]

ALLOWED_ACRONYMS = {
    # Core tech / protocols
    "AI", "LLM", "API", "CLI", "CI", "CD", "CPU", "GPU",
    "JSON", "YAML", "HTML", "HTTP", "HTTPS", "URI", "UUID",
    "CSV", "PDF", "RFC", "SDK", "URL", "REST", "CSS",
    "TLS", "SSH", "DNS", "TCP", "UDP", "SQL", "GRPC",
    "RBAC", "OIDC", "JWT", "HMAC", "SHA", "RSA", "AES",
    "CBC", "GCM", "PEM", "CORS", "CSRF", "PII", "SSE", "SSO",
    "RPC", "CDN", "NTP", "OTLP", "NATS", "WAN", "HSM",
    "ACL", "KMS", "AUTH", "PAT", "SRC", "DOM", "ENV", "DIR", "PATH",
    # DeepSigma / Coherence Ops primitives
    "DLR", "RS", "DS", "MG", "IRIS", "PRIME", "GPE", "GPR", "TTL",
    "RAL", "DTE", "ICR", "PCR", "TEC", "CTEC", "DISR", "ABP",
    "DRT", "DEC", "CLM", "MDPT", "EDGE", "DRIFT", "PATCH",
    "SIGNAL", "RECALL", "CLAIM", "GATE", "SYNC", "CORE",
    "FEEDS", "ALS", "DLQ", "PUB", "SUB", "ACK", "INBOX", "OTHER", "POSIX", "ASGI", "WSGI",
    "BEACON", "SKEW", "BOOT", "RETCON", "PEGI", "CERO", "ESRB",
    "RONIN", "DLC", "DRI", "BOE", "SLO", "CMS", "MVP",
    # Standards / formats / compliance
    "SHACL", "SPARQL", "SPDX", "SBOM", "RDF", "OWL",
    "OTEL", "MCP", "NDJSON", "JSONL", "JSONB", "SVG",
    "MIT", "GDPR", "HIPAA", "NPPA", "PIPL", "ISO", "UTC",
    # Technical / CI terms
    "PASS", "FAIL", "HIGH", "LOW", "PEP", "AST",
    "PYPI", "GHCR", "KPI", "SLA", "ROM", "FAQ", "DEMO",
    "FULL", "TEST", "BATCH", "DIFF", "SPEC", "GUID",
    # HTTP verbs / SQL keywords (appear in uppercase in docs)
    "GET", "POST", "PUT", "DELETE", "UPDATE",
    "SELECT", "INSERT", "INTO", "VALUES", "CREATE",
    "EXISTS", "TABLE", "WHERE", "UNIQUE", "DESC",
    "LIMIT", "OFFSET", "COUNT", "GROUP",
    # Common English words appearing in uppercase labels/headings
    "RED", "GREEN", "YELLOW", "ORANGE", "STATUS", "TEXT",
    "ERROR", "WARN", "NULL", "FROM", "KEY", "ALL", "NOT",
    "WHY", "WHAT", "NOW", "OFF", "AND", "MUST",
    "README", "SCORE", "RISK", "ORDER", "BLOCK", "REVIEW",
    "MEDIUM", "REJECT", "MEMORY", "DEFER", "SCOPE", "ACTIVE",
    "PASSED", "FAILED", "EXPIRE", "TODAY", "TRUTH", "HUMAN",
    "ICON", "ROLE", "INFO", "LINE", "PIPE", "EPIC",
    "YYYY", "NNNN", "VALID", "ACTION", "SERIAL", "SET",
    "ACCESS", "LOCAL", "NEW", "FORM", "HALF", "LIFE",
    "DRAFT", "RESULT", "SHOULD", "ABOUT", "SHOW", "SWITCH",
    "DENIED", "TIMING", "LAG", "WEST", "BROKEN",
    # Project domain short codes (dashboards, fields, variable prefixes)
    "REG", "OPS", "CLN", "CRE", "OBJ", "PLT", "FIN",
    "MON", "DAT", "ZIP", "REQ", "MSG", "ACC", "REV",
    "CTR", "EXEC", "CONF", "CORR", "CAP", "BIO", "TECH",
    "NAV", "VFX", "XXX", "RFP", "OPP", "HIRE", "CPT",
    "RFS", "COMP", "MAJ", "AAA", "TOCTOU", "ASM",
    "FRAN", "DEL", "AITECH", "TRM", "OBS", "INF",
    "FCT", "NRM", "CON", "ESC", "SOL", "TPS", "HUD",
    "ITCO", "IDI", "EET",
    # Business / ops terms used in generic scenarios
    "SRE", "ERP", "ITSM", "CRM", "SKU", "HITL",
    "RUN", "UTF", "INC", "SUP", "EVD", "PRM", "RCF", "CCF",
    "GAP", "TRC", "SFC", "CTI", "CMO", "ABC",
    "FFP", "DDR", "APAC", "JST",
    "CNO", "IDIQ", "RAC",
    # Security terms
    "XSS", "CRUD", "RAM", "ROI", "TPM", "AWS", "GCP",
    "PKCS", "PIV", "SOC", "GRC", "GRAC", "KRI", "MTTR",
    # Gaming / entertainment (used in rating system examples)
    "XBOX", "DAU", "NPC", "RPG", "USK", "STEAM",
    # Ontology / semantic web
    "RDFS", "LCEL", "SKOS", "PROV",
    # Healthcare example terms (used in generic lattice scenarios)
    "EHR", "ICU", "DRG", "CICU", "CPO", "NICU", "PACU",
    "PHI", "ASHP", "AWHONN", "REMS", "SUD", "ASAM",
    "ICD", "WHO", "TPA",
    # Compliance frameworks
    "LGPD", "CCPA", "SOX", "CFR", "DPA", "DSAR",
    # Government / cleared-program terms (allowlisted for generic scenarios)
    "TSA", "INTEL", "SCI", "DBIDS", "DEA", "ISSO", "GOV",
    "SGT", "ISSM", "IAA", "OIG", "CONUS", "CUI", "ATO",
    "SSI", "USC", "SCIF", "OCONUS", "ISMP", "POA",
    "NAICS", "IGCE", "DCAA", "GWAC", "BPA", "SOP",
    "CFO", "CTO", "CDI", "FTE", "RFI",
    # Additional common English / code in uppercase
    "DECIDE", "AMBER", "SEAL", "STALE", "SEALED", "CLAIMS",
    "ONLY", "SEV", "LRU", "DID", "TRACE", "USAGE", "TOP",
    "ACID", "ALLOW", "BID", "BOARD", "BOM", "CANON",
    "CAUSED", "CLEAN", "CLOSED", "COMMIT", "CONST", "COPY",
    "DATA", "DEG", "DENY", "DOTALL", "EMPTY", "ENGINE",
    "EST", "EXPORT", "FIX", "GATES", "GLOBAL", "GPT",
    "HALT", "HARD", "HASH", "HPA", "IGNORE", "IMPORT",
    "IOS", "LAN", "LIVE", "LOCK", "MENU", "MODE", "MOVE",
    "NFC", "NOTE", "OFFER", "OPEN", "OPPS", "OSS", "OUTPUT",
    "PKG", "PLANS", "POL", "POLICY", "POP", "PRAGMA",
    "QPS", "QUERY", "RAG", "RID", "RISKS", "ROLES",
    "RPS", "RULES", "SAMPLE", "SDR", "SECRET", "SKIP",
    "STYLES", "SYSTEM", "TITLES", "TRUE", "TTK", "UNK",
    "USD", "VRAM", "WAL", "WIP", "YES",
    "AUC", "CEROZ", "CSOM", "GEOINT", "CID",
    # GitHub issue export metadata (author names, label colors, states)
    "BRYAN", "DAVID", "WHITE", "MERGED", "EDEDED", "NEEDS",
    # Infrastructure / runtime terms
    "WASM", "PREFIX", "ROOT", "TENANT", "REPO", "HOT", "WARM",
    "COLD", "TOTAL", "PNG", "MESH", "HEALTH", "ASCII", "NIST",
    "CSF", "DOCKER", "NONCE", "MOCK", "ARGS", "ARG", "HEAD",
    "AUTO", "PERF", "OAUTH", "BENCH", "TESTDB", "TODO", "TBD",
    "DONE", "NONE", "PARENT", "PACKET", "USER", "OWNER", "OUT",
    "OLD", "AFTER", "NAME", "ONLINE", "PUBLIC", "SAFE",
    # Project short codes (coherence, signals, services)
    "COH", "LADDER", "SWC", "SRV", "CDS", "EVT", "SIG", "YEL",
    "TLE", "ENT", "PKT", "DRF", "BOGUS", "GOLDEN", "GOLD",
    "REC", "SER",
    # Security / supply-chain / identity
    "SLSA", "SPIFFE", "PVC", "AAD", "SSR", "RACI", "AML",
    "RNG", "OSI", "RSS", "XRAY",
    # Test / placeholder tokens
    "XYZ", "BBBB", "AAAA", "NOPE", "III", "PILOT", "ECON",
    # Semver / compat terminology
    "MAJOR", "MINOR",
    # Authority / governance terms
    "REFUSE", "REFUSAL", "REFUSED", "REF",
    # Fixture / test data terms
    "VALUE", "TIER", "SOURCE", "SUM", "PRJ", "TSK", "PMP",
    "APR", "YOU", "ARE",
    # Domain mode state machine / pipeline step names
    "FROZEN", "LOAD", "INGEST", "DELTA", "REOPS", "MONEY",
    # JRM (Judgment Refinement Module) adapters, pipeline, fixtures
    "JRM", "SURI", "SNRT", "AGNT", "MAL", "EVE", "GID", "SID",
    "DST", "PORT", "PROTO", "RAT", "GPL", "SCAN", "TLD", "USEC",
    "NOTIFY",
}

SCAN_EXTS = {".md", ".txt", ".py", ".html", ".yaml", ".yml", ".json", ".toml"}
SKIP_DIRS = {".git", ".github", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".pytest_cache"}
SKIP_FILES = {"issues_all.json", "prs_merged.json"}  # Generated GitHub export data


# ----------------------------
# Types
# ----------------------------

@dataclass
class Finding:
    file: Path
    line_no: int
    kind: str   # "DENY" or "HEUR"
    token: str
    line: str


# ----------------------------
# File walking
# ----------------------------

def iter_files(root: Path, paths: List[str]) -> Iterable[Path]:
    for p in paths:
        base = (root / p).resolve()
        if not base.exists():
            continue
        if base.is_file():
            if base.suffix.lower() in SCAN_EXTS:
                yield base
            continue
        for f in base.rglob("*"):
            if f.is_dir():
                continue
            if any(part in SKIP_DIRS for part in f.parts):
                continue
            if f.suffix.lower() not in SCAN_EXTS:
                continue
            if f.name in SKIP_FILES:
                continue
            yield f


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


# ----------------------------
# AutoFix
# ----------------------------

def apply_replacements(text: str) -> str:
    items = sorted(REPLACEMENTS.items(), key=lambda kv: len(kv[0]), reverse=True)
    out = text
    for k, v in items:
        pat = re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE)
        out = pat.sub(v, out)
    return out


# ----------------------------
# Heuristic masking (ignore code blocks)
# ----------------------------

def _mask_span_preserve_newlines(text: str, start: int, end: int) -> str:
    span = text[start:end]
    masked = "".join("\n" if ch == "\n" else " " for ch in span)
    return text[:start] + masked + text[end:]


def mask_code_blocks_for_heuristics(path: Path, text: str) -> str:
    """
    Masks code blocks so HEURISTIC_PATTERNS don't flag acronyms inside code.

    Applies to:
      - Markdown fenced blocks: ``` ... ``` and ~~~ ... ~~~
      - Markdown inline code: `...`
      - HTML <pre>...</pre> blocks
    """
    ext = path.suffix.lower()
    out = text

    if ext in {".md", ".txt"}:
        fence_re = re.compile(
            r"(^```[^\n]*\n.*?^```[ \t]*$)|(^~~~[^\n]*\n.*?^~~~[ \t]*$)",
            re.MULTILINE | re.DOTALL,
        )
        for m in reversed(list(fence_re.finditer(out))):
            out = _mask_span_preserve_newlines(out, m.start(), m.end())

        inline_re = re.compile(r"`[^`\n]+`")
        for m in reversed(list(inline_re.finditer(out))):
            out = _mask_span_preserve_newlines(out, m.start(), m.end())

    if ext == ".html":
        pre_re = re.compile(r"<pre\b[^>]*>.*?</pre>", re.IGNORECASE | re.DOTALL)
        for m in reversed(list(pre_re.finditer(out))):
            out = _mask_span_preserve_newlines(out, m.start(), m.end())

    return out


# ----------------------------
# Scanning
# ----------------------------

def scan_content(path: Path, text: str) -> List[Finding]:
    findings: List[Finding] = []
    lines = text.splitlines()

    # DENYLIST scan (full text, word-boundary enforced)
    deny_patterns = [(t, re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE)) for t in FORBIDDEN_TERMS]
    for i, line in enumerate(lines, start=1):
        for token, pat in deny_patterns:
            if pat.search(line):
                findings.append(Finding(path, i, "DENY", token, line))

    # HEURISTICS scan (masked text)
    heur_text = mask_code_blocks_for_heuristics(path, text)
    heur_lines = heur_text.splitlines()

    for i, masked_line in enumerate(heur_lines, start=1):
        for name, pat in HEURISTIC_PATTERNS:
            for m in pat.finditer(masked_line):
                tok = m.group(0)

                if name.startswith("Likely agency/program acronym"):
                    if tok in ALLOWED_ACRONYMS:
                        continue

                original_line = lines[i - 1] if (i - 1) < len(lines) else ""
                findings.append(Finding(path, i, "HEUR", name, original_line))

    return findings


# ----------------------------
# Main
# ----------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="Auto-fix known forbidden terms via replacements map.")
    ap.add_argument(
        "--paths",
        nargs="*",
        default=[
            "docs", "enterprise/docs", "enterprise/tests", "enterprise/release_kpis",
            "edge", "src", "packages", "reference",
            "README.md", "CONTRIBUTING.md", "CHANGELOG.md",
            "SECURITY.md", "EDITION_DIFF.md",
        ],
        help="Paths to scan (files or folders).",
    )
    args = ap.parse_args()

    root = Path(os.getcwd()).resolve()

    all_findings: List[Finding] = []
    changed_files: List[Path] = []

    for f in sorted(set(iter_files(root, args.paths))):
        original = read_text(f)

        updated = original
        if args.fix:
            updated = apply_replacements(updated)
            if updated != original:
                f.write_text(updated, encoding="utf-8")
                changed_files.append(f)

        all_findings.extend(scan_content(f, updated))

    deny = [x for x in all_findings if x.kind == "DENY"]
    heur = [x for x in all_findings if x.kind == "HEUR"]

    if args.fix and changed_files:
        print("\n[GPE] AutoFix updated files:")
        for cf in changed_files:
            print(f"  - {cf}")

    if all_findings:
        print("\n[GPE] Findings:")
        for x in all_findings[:300]:
            print(f"{x.file}:{x.line_no} [{x.kind}] {x.token}\n  {x.line.strip()}")
        if len(all_findings) > 300:
            print(f"... {len(all_findings) - 300} more findings truncated ...")

    print("\n[GPE] Totals:")
    print(f"  DENY (forbidden): {len(deny)}")
    print(f"  HEUR (heuristics): {len(heur)}")
    print(f"  AutoFix files changed: {len(changed_files)}")

    if len(deny) > 0 or len(heur) > 0:
        print("\n[GPE] FAIL: Repo is not 100% generic primitives yet.")
        print("      Fix findings or tune allowlists. For AutoFix run: python scripts/domain_scrub.py --fix")
        return 1

    print("\n[GPE] PASS: 100% generic primitives enforced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
