.PHONY: demo core-demo core-baseline test-money test-excel

demo:
	bash run_money_demo.sh

core-demo:
	bash run_money_demo.sh

core-baseline:
	python core_baseline.py

test-money:
	python -m pytest tests/test_money_demo.py -q

test-excel:
	python -m pytest tests/test_excel_first_money_demo.py -q
