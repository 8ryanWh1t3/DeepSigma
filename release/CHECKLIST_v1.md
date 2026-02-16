# Release Readiness Checklist — v1

> **What:** Gate-check before any tagged release.
>
> **So What:** Nothing ships unless these pass. Copy this file into an issue or PR and check each box.

---

## ✅ 1. Tests

```bash
# Run full test suite
python -m pytest tests/ -v

# Expected: all tests pass, zero failures
```

- [ ] `pytest tests/` passes with zero failures
- [ ] No skipped tests without documented reason

---

## ✅ 2. Lint & Format

```bash
# Ruff lint
python -m ruff check .

# Ruff format check
python -m ruff format --check .
```

- [ ] `ruff check .` reports zero errors
- [ ] `ruff format --check .` reports no changes needed

---

## ✅ 3. Schema Validation

```bash
# Validate LLM data model examples against schemas
python llm_data_model/05_validation/validate_examples.py

# Validate coherence_ops sample data
python -m coherence_ops audit ./coherence_ops/examples/sample_episodes.json
```

- [ ] `validate_examples.py` exits 0 (all examples pass)
- [ ] `coherence_ops audit` completes without crash
- [ ] All JSON files in `examples/` parse without errors:
  ```bash
  find examples/ -name "*.json" -exec python -m json.tool {} > /dev/null \;
  ```

---

## ✅ 4. SHACL Validation (if RDF/SHACL present)

```bash
# Check if SHACL shapes validate
ls rdf/*.ttl
# If present, run pyshacl or equivalent
```

- [ ] SHACL shapes validate against sample data (or N/A if not yet wired)

---

## ✅ 5. Demo Walkthrough

```bash
# Run the end-to-end pipeline
python -m coherence_ops.examples.e2e_seal_to_report

# Run the ship-it demo
python -m coherence_ops demo ./coherence_ops/examples/sample_episodes.json
```

- [ ] `e2e_seal_to_report` runs all 3 examples without error
- [ ] `demo` command produces coherence score output
- [ ] Hero demo steps in [`HERO_DEMO.md`](../HERO_DEMO.md) can be followed without errors

---

## ✅ 6. Docs Link Check

```bash
# Find all markdown links and check for dead references
# Quick manual check:
grep -rn '](.*\.md)' *.md canonical/ category/ ontology/ runtime/ metrics/ roadmap/ docs/ | head -50
```

- [ ] No dead links in `README.md`, `START_HERE.md`, `HERO_DEMO.md`, `NAV.md`
- [ ] `docs/99-docs-map.md` routing table is accurate
- [ ] All `/canonical/` spec files have valid internal links

---

## ✅ 7. Version Bump

- [ ] `pyproject.toml` version bumped
- [ ] `CHANGELOG.md` updated with release notes
- [ ] `coherence_ops/__init__.py` version string matches
- [ ] All canonical specs have `version:` in YAML frontmatter that matches release

---

## ✅ 8. Schema Consistency

- [ ] `specs/*.schema.json` files have `$schema` and `$id` fields
- [ ] Schema versions match `pyproject.toml` release version
- [ ] No orphan schemas (every schema referenced from at least one spec or README)

---

## ✅ 9. CI/CD

- [ ] GitHub Actions pass on the release branch
- [ ] No security advisories flagged by Dependabot

---

## ✅ 10. Final Sanity

- [ ] Clone the repo fresh and run:
  ```bash
  git clone https://github.com/8ryanWh1t3/DeepSigma.git /tmp/ds-check
  cd /tmp/ds-check
  pip install -r requirements.txt
  python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json
  ```
- [ ] Score command produces valid JSON output
- [ ] No import errors or missing dependencies

---

## Release Approval

- [ ] All 10 sections above are green
- [ ] PR approved by at least one reviewer
- [ ] Tag created: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] GitHub Release published with changelog excerpt
