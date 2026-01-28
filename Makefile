SHELL := /bin/bash

.PHONY: help test test-frontend test-backend test-pactfix lint publish build-pactfix clean

help:
	@echo "Targets:"
	@echo "  make test           - run all tests (frontend e2e + pactfix-py)"
	@echo "  make test-frontend  - run Playwright e2e tests"
	@echo "  make test-pactfix   - run pactfix-py pytest suite"
	@echo "  make test-backend   - basic python syntax check for server.py"
	@echo "  make publish        - build + upload python package pactfix (requires twine credentials)"


test: test-backend test-pactfix test-frontend


test-frontend:
	npm test


test-backend:
	python -m py_compile server.py


test-pactfix:
	python -m pytest -q


build-pactfix:
	python -m pip install -q --upgrade build twine
	python -m build --sdist --wheel


publish: build-pactfix
	@if [ -z "$$TWINE_USERNAME" ] || [ -z "$$TWINE_PASSWORD" ]; then \
		echo "TWINE_USERNAME/TWINE_PASSWORD must be set (or use TWINE_USERNAME=__token__ and TWINE_PASSWORD=pypi-...)"; \
		exit 2; \
	fi
	python -m twine upload dist/*


clean:
	rm -rf dist build .pytest_cache test-results pactfix-py/.pytest_cache pactfix-py/dist pactfix-py/build pactfix-py/*.egg-info
