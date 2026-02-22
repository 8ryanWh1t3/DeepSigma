.PHONY: ci pilot-in-a-box why-60s no-dupes

ci:
	python scripts/compute_ci.py

pilot-in-a-box:
	python scripts/pilot_in_a_box.py

why-60s:
	python scripts/why_60s_challenge.py

no-dupes:
	python3 scripts/check_no_dupe_files.py
