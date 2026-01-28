# Pactfix

Multi-language code and config file analyzer and fixer.

## Supported Languages

### Code
- Bash
- Python
- PHP
- JavaScript
- Node.js

### Config Files
- Dockerfile
- docker-compose.yml
- SQL
- Terraform
- Kubernetes YAML
- nginx config
- GitHub Actions
- Ansible playbooks

## Installation

```bash
pip install -e .
```

## CLI Usage

```bash
# Analyze single file
pactfix input.py -o output.py --log-file log.json -v

# Batch process directory
pactfix --batch ./src

# Fix all example files
pactfix --fix-all

# Output as JSON
pactfix input.py --json
```

## API Server

```bash
# Run server
python -m pactfix.server

# Or with custom port
PORT=8000 python -m pactfix.server
```

### Endpoints

- `GET /api/health` - Health check
- `POST /api/analyze` - Analyze code
- `POST /api/detect` - Detect language
- `GET /api/languages` - List supported languages

## Docker

```bash
docker build -t pactfix .
docker run -p 5000:5000 pactfix
```
