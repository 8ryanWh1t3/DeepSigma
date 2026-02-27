.PHONY: demo core-demo core-baseline test-core core-ci \
	enterprise-demo test-enterprise enterprise-ci \
	edition-guard secret-scan domain-scrub security-gate openapi-check version-sync-check \
	test-money release-artifacts pulse-insights \
	icr-health pcr-health tec-ctec health-summary health-v2 \
	icr-health-gh pcr-health-gh health-v2-gh tec \
	roadmap-refresh roadmap-gate \
	milestone-gate issue-label-gate kpi-issues kpi stability \
	validate-feeds test-feeds-bus test-feeds-ingest test-feeds-consumers test-feeds-canon test-feeds \
	constitution-gate \
	verify-release-artifacts validate-kpi-eligibility tec-sensitivity

demo:
	bash run_money_demo.sh

core-demo:
	bash run_money_demo.sh

enterprise-demo:
	bash run_enterprise_demo.sh

core-baseline:
	python core_baseline.py

test-money:
	python -m pytest tests/test_money_demo.py -q

test-enterprise:
	python -m pytest tests-enterprise/ -q

test-core:
	python -m pytest tests/ -q

core-ci: edition-guard core-demo core-baseline test-core

enterprise-ci: edition-guard enterprise-demo test-enterprise

edition-guard:
	@echo "==> Guard: CORE must not import ENTERPRISE"
	@python enterprise/scripts/edition_guard.py

secret-scan:
	@echo "==> Secret scan (lightweight patterns)"
	@python enterprise/scripts/secret_scan.py

domain-scrub:
	@echo "==> GPE: Generic Primitive Enforcement scan"
	@python scripts/domain_scrub.py

security-gate: secret-scan
	@python enterprise/scripts/security_proof_pack.py

openapi-check:
	@test -f enterprise/docs/api/openapi.json
	@echo "PASS: enterprise/docs/api/openapi.json present"

version-sync-check:
	@python enterprise/scripts/version_sync_check.py

release-artifacts:
	python enterprise/scripts/build_release_artifacts.py

pulse-insights:
	python enterprise/scripts/pulse_insights.py

icr-health:
	python enterprise/scripts/icr_health_watcher.py --snapshot

pcr-health:
	python enterprise/scripts/pr_complexity_watcher.py --snapshot

tec-ctec:
	python enterprise/scripts/tec_ctec.py --snapshot

tec: tec-ctec

health-summary:
	python enterprise/scripts/health_summary.py

health-v2: icr-health pcr-health tec-ctec health-summary

icr-health-gh:
	python enterprise/scripts/icr_health_watcher.py --from-gh --snapshot

pcr-health-gh:
	python enterprise/scripts/pr_complexity_watcher.py --from-gh --snapshot

health-v2-gh: icr-health-gh pcr-health-gh tec-ctec health-summary

roadmap-refresh:
	python enterprise/scripts/roadmap_forecast.py
	python enterprise/scripts/render_roadmap_badge.py
	python enterprise/scripts/render_roadmap_timeline.py

roadmap-gate:
	python enterprise/scripts/roadmap_scope_gate.py

milestone-gate:
	python enterprise/scripts/validate_v2_1_0_milestone.py

issue-label-gate:
	python enterprise/scripts/issue_label_gate.py

kpi-issues:
	python enterprise/scripts/kpi_from_issues.py

stability:
	python enterprise/scripts/nonlinear_stability.py

kpi:
	cd enterprise && python scripts/kpi_run.py

validate-feeds:
	python -m pytest tests/test_feeds_schemas.py tests/test_feeds_envelope.py tests/test_feeds_cli.py -v

test-feeds-bus:
	python -m pytest tests/test_feeds_bus.py -v

test-feeds-ingest:
	python -m pytest tests/test_feeds_ingest.py -v

test-feeds-consumers:
	python -m pytest tests/test_feeds_consumers.py -v

test-feeds-canon:
	python -m pytest tests/test_feeds_canon.py -v

test-feeds: validate-feeds test-feeds-bus test-feeds-ingest test-feeds-consumers test-feeds-canon

site-content:
	python scripts/generate_site_content.py

constitution-gate:
	python scripts/constitution_gate.py

verify-release-artifacts:
	python scripts/verify_release_artifacts.py

validate-kpi-eligibility:
	python scripts/validate_kpi_eligibility.py

tec-sensitivity:
	python enterprise/scripts/tec_sensitivity.py
