.PHONY: install test check validate site

install:
	python3 -m pip install -e '.[dev]'

test:
	python3 -m unittest discover -s tests -v

check:
	python3 -m ruff check src tests
	python3 -m unittest discover -s tests -v

validate:
	python3 -m svea_eval validate

site:
	python3 -m svea_eval build-site
