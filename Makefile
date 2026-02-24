.PHONY: demo core-demo enterprise-demo core-baseline test-money test-enterprise release-artifacts

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

release-artifacts:
	python enterprise/scripts/build_release_artifacts.py
