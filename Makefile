.PHONY: setup data sql analysis all test clean

PYTHON ?= python3

setup:
	$(PYTHON) -m pip install -r requirements.txt

data:
	$(PYTHON) -m src.generate_data
	$(PYTHON) -m src.build_database

sql:
	$(PYTHON) -m src.run_sql_analysis

analysis:
	$(PYTHON) -m src.analyze

all: data sql analysis

test:
	$(PYTHON) -m unittest discover -s tests -v

clean:
	rm -f data/wealth_analytics.db
	rm -f data/raw/*.csv outputs/tables/*.csv outputs/charts/*.png outputs/model_summary.txt

