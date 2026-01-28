# Pactfix

Multi-language code and config file analyzer and fixer with Docker sandbox support.

## Supported Languages

### Code

- Bash, Python, PHP, JavaScript, Node.js
- TypeScript, Go, Rust, Java, C#, Ruby

### Config Files

- Dockerfile, docker-compose.yml
- SQL, Terraform, Kubernetes YAML
- nginx config, GitHub Actions, Ansible playbooks
- Apache, Systemd, Makefile

## Installation

```bash
pip install -e .
```

## CLI Usage

### Single File Analysis

```bash
pactfix input.py -o output.py --log-file log.json -v
pactfix input.py --json
```

### Project Scanning (NEW)

```bash
# Scan and fix all files in project, add comments above changed lines
pactfix --path ./ --comment

# Scan project and run in Docker sandbox
pactfix --path ./ --sandbox

# Scan, fix, and run tests in sandbox
pactfix --path ./ --sandbox --test

# Verbose output
pactfix --path ./ --comment -v
```

### Sandbox Mode (NEW)

```bash
# Setup sandbox only (without fixing)
pactfix --sandbox-only ./my-project

# Create Dockerfiles for all languages
pactfix --init-dockerfiles ./dockerfiles/
```

### Batch Processing

```bash
pactfix --batch ./src
pactfix --fix-all
```

## Features

### `--path` - Project Scanning

Scans entire project directory, analyzes all supported files, and saves:
- Fixed files to `.pactfix/fixed/`
- Report to `.pactfix/report.json`

### `--comment` - Fix Comments

Adds comment above each changed line explaining the fix:

```python
# pactfix: Added parentheses to print() (was: print "hello")
print("hello")
```

### `--sandbox` - Docker Sandbox
Creates isolated Docker environment in `.pactfix/` folder:
- Auto-detects project language
- Generates appropriate Dockerfile
- Creates docker-compose.yml
- Copies fixed files for testing

### Supported Sandbox Languages

| Language   | Base Image              |
|------------|-------------------------|
| Python     | python:3.11-slim        |
| Node.js    | node:20-slim            |
| TypeScript | node:20-slim            |
| Go         | golang:1.21-alpine      |
| Rust       | rust:1.75-slim          |
| Java       | eclipse-temurin:21-jdk  |
| PHP        | php:8.3-cli             |
| Ruby       | ruby:3.3-slim           |
| C#         | dotnet/sdk:8.0          |
| Bash       | ubuntu:22.04            |
| Terraform  | hashicorp/terraform:1.6 |
| Ansible    | python:3.11-slim        |

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
