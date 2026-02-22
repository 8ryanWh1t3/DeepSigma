.PHONY: pilot-in-a-box why-60s no-dupes

pilot-in-a-box:
	python3 scripts/pilot_in_a_box.py

why-60s:
	python3 scripts/why_60s_challenge.py

no-dupes:
	python3 scripts/check_no_dupe_files.py
