.PHONY: ci pilot-in-a-box why-60s no-dupes kpi kpi-render kpi-badge kpi-gate

ci:
	python scripts/compute_ci.py

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

kpi-badge:
	python scripts/render_badge.py --kpi release_kpis/kpi_$(shell cat release_kpis/VERSION.txt).json --out release_kpis/badge_latest.svg

kpi-gate:
	python scripts/kpi_gate.py
