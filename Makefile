SHELL := /bin/bash

# Include .env file if it exists
-include .env
export

.PHONY: help test test-frontend test-backend test-pactfix test-sandbox test-sandbox-tests lint publish build-pactfix bump-patch clean build run stop docker-build docker-run docker-stop docker-clean down

PACTFIX_DIR ?= pactfix-py
PORT ?= 8081

help:
	@echo "Targets:"
	@echo "  make test           - run all tests (frontend e2e + pactfix-py)"
	@echo "  make test-frontend  - run Playwright e2e tests"
	@echo "  make test-pactfix   - run pactfix-py pytest suite"
	@echo "  make test-sandbox   - run pactfix sandbox smoke test on all test-projects"
	@echo "  make test-sandbox-tests - run sandbox smoke test + run in-container test commands (--test)"
	@echo "  make test-backend   - basic python syntax check for server.py"
	@echo "  make publish        - build + upload python package pactfix (requires twine credentials)"
	@echo "  make build          - build Docker image for pactown-debug"
	@echo "  make run            - run Docker container (builds if needed)"
	@echo "  make stop           - stop and remove running container"
	@echo "  make clean          - remove python build/test artifacts"
	@echo "  make docker-build   - build Docker image for pactown-debug"
	@echo "  make docker-run     - run Docker container (builds if needed)"
	@echo "  make docker-stop    - stop and remove running container"
	@echo "  make docker-clean   - remove Docker image and containers"
	@echo "  make down           - stop and remove containers (alias for docker-clean)"

test: test-backend test-pactfix test-frontend

test-frontend:
	npm test

test-backend:
	python -m py_compile server.py
	python -m unittest discover -s tests -q

test-pactfix:
	cd $(PACTFIX_DIR) && python -m pytest -q

test-sandbox:
	cd $(PACTFIX_DIR) && ./scripts/test-sandboxes.sh

test-sandbox-tests:
	cd $(PACTFIX_DIR) && ./scripts/test-sandboxes.sh --test

build-pactfix:
	cd $(PACTFIX_DIR) && python -m pip install -q --upgrade build twine
	cd $(PACTFIX_DIR) && python -m build --sdist --wheel

bump-patch:
	python -c 'from pathlib import Path; import re; pyproject = Path("$(PACTFIX_DIR)") / "pyproject.toml"; content = pyproject.read_text(encoding="utf-8"); pattern = re.compile(r"^(version\s*=\s*\")(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(\")", re.MULTILINE); match = pattern.search(content); assert match, "Could not find version in pyproject.toml"; major = int(match.group("major")); minor = int(match.group("minor")); patch = int(match.group("patch")) + 1; new_version = f"{major}.{minor}.{patch}"; updated = pattern.sub(rf"\g<1>{new_version}\g<5>", content, count=1); pyproject.write_text(updated, encoding="utf-8"); print(f"Bumped pactfix version to {new_version}")'

publish: bump-patch build-pactfix
	cd $(PACTFIX_DIR) && python -m twine upload dist/*

clean:
	rm -rf dist build .pytest_cache test-results \
		$(PACTFIX_DIR)/.pytest_cache $(PACTFIX_DIR)/dist $(PACTFIX_DIR)/build $(PACTFIX_DIR)/*.egg-info

build:
	docker build -t pactown-debug .

run: build
	@if ! docker ps -q -f name=pactown-debug | grep -q .; then \
		docker run -d --name pactown-debug -p $(PORT):8080 --env-file .env --rm pactown-debug; \
		echo "Container started: http://localhost:$(PORT)"; \
	else \
		echo "Container already running: http://localhost:$(PORT)"; \
	fi

stop:
	@if docker ps -q -f name=pactown-debug | grep -q .; then \
		docker stop pactown-debug; \
		echo "Container stopped."; \
	else \
		echo "Container not running."; \
	fi

docker-build:
	docker build -t pactown-debug .

docker-run: docker-build
	@if ! docker ps -q -f name=pactown-debug | grep -q .; then \
		docker run -d --name pactown-debug -p $(PORT):8080 --env-file .env --rm pactown-debug; \
		echo "Container started: http://localhost:$(PORT)"; \
	else \
		echo "Container already running: http://localhost:$(PORT)"; \
	fi

docker-stop:
	@if docker ps -q -f name=pactown-debug | grep -q .; then \
		docker stop pactown-debug; \
		echo "Container stopped."; \
	else \
		echo "Container not running."; \
	fi

docker-clean: docker-stop
	@if docker images -q pactown-debug | grep -q .; then \
		docker rmi pactown-debug; \
		echo "Image removed."; \
	else \
		echo "Image not found."; \
	fi

down: docker-clean
