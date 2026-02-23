.PHONY: ci demo pilot-in-a-box why-60s no-dupes kpi kpi-render kpi-composite kpi-badge kpi-gate kpi-issues issue-label-gate issues-review tec lock-update build docker release-check release-check-strict version-sync-check pilot-pack scale-benchmark reencrypt-benchmark openapi-docs openapi-check security-gate security-demo security-audit-pack authority-ledger-export roadmap-forecast roadmap-badge roadmap-timeline roadmap-gate roadmap-refresh stability

ci:
	python scripts/compute_ci.py

demo:
	bash run_money_demo.sh

pilot-in-a-box:
	python scripts/pilot_in_a_box.py

why-60s:
	python scripts/why_60s_challenge.py

no-dupes:
	python3 scripts/check_no_dupe_files.py

kpi:
	python scripts/kpi_run.py

kpi-render:
	python scripts/render_radar.py --kpi release_kpis/kpi_$(shell cat release_kpis/VERSION.txt).json --outdir release_kpis

kpi-composite:
	python scripts/render_composite_radar.py

kpi-badge:
	python scripts/render_badge.py --kpi release_kpis/kpi_$(shell cat release_kpis/VERSION.txt).json --out release_kpis/badge_latest.svg

kpi-gate:
	python scripts/kpi_gate.py

kpi-issues:
	python scripts/kpi_from_issues.py

issue-label-gate:
	python scripts/issue_label_gate.py

issues-review:
	bash scripts/issues_review.sh
	python scripts/issue_label_gate.py

tec:
	bash scripts/export_repo_telemetry.sh
	python scripts/tec_estimate.py

lock-update:
	bash scripts/update_locks.sh

build:
	python -m pip install --upgrade pip
	pip install -c requirements/locks/release-build.txt build
	python -m build

docker:
	docker build -t ghcr.io/8ryanwh1t3/deepsigma:local .

release-check:
	python scripts/release_check.py

release-check-strict:
	RELEASE_CHECK_REQUIRE_MAIN_HEAD=1 python scripts/release_check.py

version-sync-check:
	python scripts/check_release_version_sync.py

pilot-pack:
	python scripts/pilot_pack.py

scale-benchmark:
	bash scripts/run_scale_stack.sh

reencrypt-benchmark:
	python scripts/reencrypt_benchmark.py $(ARGS)

openapi-docs:
	python scripts/export_openapi.py

openapi-check:
	python scripts/export_openapi.py
	python scripts/check_openapi_spec.py
	git diff --exit-code -- docs/api/openapi.json docs/api/index.html docs/api/README.md

security-gate:
	python scripts/crypto_misuse_scan.py

security-demo:
	python scripts/reencrypt_demo.py

security-audit-pack:
	python scripts/security_audit_pack.py

authority-ledger-export:
	python scripts/export_authority_ledger.py

roadmap-forecast:
	python scripts/roadmap_forecast.py

roadmap-badge:
	python scripts/render_roadmap_badge.py

roadmap-timeline:
	python scripts/render_roadmap_timeline.py

roadmap-gate:
	python scripts/roadmap_scope_gate.py

roadmap-refresh:
	python scripts/roadmap_forecast.py
	python scripts/render_roadmap_badge.py
	python scripts/render_roadmap_timeline.py
	python scripts/roadmap_scope_gate.py

stability:
	python scripts/nonlinear_stability.py
