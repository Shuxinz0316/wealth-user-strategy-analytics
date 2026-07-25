.PHONY: install run test

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m src.pipeline

test:
	$(PYTHON) -m unittest discover -s tests -v
