SHELL := /bin/bash

.PHONY: help test test-frontend test-backend test-pactfix lint publish build-pactfix bump-patch clean

PACTFIX_DIR ?= pactfix-py

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
	python -m unittest -q tests.test_e2e_live_debug

test-pactfix:
	cd $(PACTFIX_DIR) && python -m pytest -q

build-pactfix:
	cd $(PACTFIX_DIR) && python -m pip install -q --upgrade build twine
	cd $(PACTFIX_DIR) && python -m build --sdist --wheel

bump-patch:
	python -c 'from pathlib import Path; import re; pyproject = Path("$(PACTFIX_DIR)") / "pyproject.toml"; content = pyproject.read_text(encoding="utf-8"); pattern = re.compile(r"^version\s*=\s*\"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\"\s*$", re.MULTILINE); match = pattern.search(content); assert match, "Could not find version in pyproject.toml"; major = int(match.group("major")); minor = int(match.group("minor")); patch = int(match.group("patch")) + 1; new_version = f"{major}.{minor}.{patch}"; updated = pattern.sub(lambda m: f"version = \"{new_version}\"", content, count=1); pyproject.write_text(updated, encoding="utf-8"); print(f"Bumped pactfix version to {new_version}")'

publish: bump-patch build-pactfix
	cd $(PACTFIX_DIR) && python -m twine upload dist/*

clean:
	rm -rf dist build .pytest_cache test-results \
		$(PACTFIX_DIR)/.pytest_cache $(PACTFIX_DIR)/dist $(PACTFIX_DIR)/build $(PACTFIX_DIR)/*.egg-info
