## [1.0.5] - 2026-01-29

### Summary

refactor(docs): code quality metrics with 6 supporting modules

### Docs

- docs: update PYPI.md

### Other

- update pactfix-py/pactfix/analyzers/docker_compose.py
- update pactfix-py/pactfix/analyzers/kubernetes.py
- update pactfix-py/pyproject.toml


## [1.0.4] - 2026-01-29

### Summary

refactor(core): cleaner code architecture

### Changes

- update playwright.config.ts

## [1.0.3] - 2026-01-29

### Summary

docs(docs): document Changelog, [1.2.0] - 2026-01-29, Added and 7 more

### Changes

- docs: update README

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-01-29

### Added
- GitLab CI support with dedicated analyzer
- Jenkinsfile support for pipeline analysis
- Enhanced language detection for YAML files
- Better error messages and fix explanations
- Comprehensive documentation with examples
- Test coverage badges and GitHub stats
- Interactive table of contents in README
- Multi-language support status table

### Fixed
- Quote positioning detection in bash command substitutions (SC1073)
- Missing fix comments for bash analysis
- Python test import issues (pytest configuration)
- E2E test stability improvements
- Stats not updating when typing code
- Example code loading issues
- Clear input functionality

### Improved
- API documentation with all endpoints (/api/analyze, /api/health, /api/snippet)
- Development setup instructions
- Project structure documentation
- Docker sandbox testing documentation

## [1.1.0] - 2026-01-28

### Added
- Real-time code analysis with debouncing
- History tracking for all fixes
- Export functionality (download/copy)
- Share via URL feature
- Statistics display (lines, chars, errors, warnings)
- Multi-language support for 20+ formats
- Docker sandbox testing
- Pactfix CLI integration

### Fixed
- Initial UI responsiveness issues
- Basic syntax highlighting

## [1.0.0] - 2026-01-20

### Added
- Initial release
- Basic bash/shell analysis
- ShellCheck integration
- Web-based UI
- Docker support
- API endpoints for analysis

---

## How to Update

### From Docker
```bash
docker-compose pull
docker-compose up -d
```

### From Source
```bash
git pull origin main
pip install -r requirements.txt
python3 server.py
```

---

## Migration Guide

### v1.0.x → v1.1.x
- No breaking changes
- New features are opt-in
- Existing API endpoints remain compatible

### v1.1.x → v1.2.x
- Enhanced language detection may identify files differently
- New analyzers for GitLab CI and Jenkinsfile
- Test structure updated (pytest.ini modified)
- update pactfix-py/tests/fixtures/terraform/main.tf
- update pactfix-py/tests/test_analyzer.py
- update playwright-report/index.html

## [1.0.1] - 2026-01-29

- docs: update CHANGELOG.md
- build: update Makefile
- chore: update version
- update pactfix-py/pactfix/sandbox.py
- update pactfix-py/scripts/test-sandboxes.sh
- update scripts/git_commit_helper.py

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
