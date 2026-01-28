# Pactfix

Multi-language code and config file analyzer and fixer with Docker sandbox support.

## Installation

```bash
pip install -e .
```

## Commands

### 1. Fix Files In Place (with comments)

```bash
pactfix --path ./my-project --comment
pactfix --path ./my-project --comment -v  # verbose
```

**What it does:**
- Scans all files in the project
- Fixes issues **directly in original files**
- Adds comment above each changed line explaining the fix
- Does NOT create `.pactfix/` directory

**Example output in file:**
```python
# pactfix: Dodano nawiasy do print() (was: print "hello")
print("hello")
```

### 2. Sandbox Mode (Docker)

```bash
pactfix --path ./my-project --sandbox
pactfix --path ./my-project --sandbox --test  # also run tests
```

**What it does:**
- Scans all files in the project
- Creates `.pactfix/` directory with:
  - `fixed/` - copy of fixed files
  - `Dockerfile` - auto-generated for detected language
  - `docker-compose.yml` - ready to run
  - `report.json` - analysis report
- Builds and runs Docker container
- Original files are NOT modified

**Directory structure:**
```
my-project/
├── .pactfix/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── fixed/
│   │   └── (fixed files)
│   ├── report.json
│   └── sandbox_output.txt
└── (original files unchanged)
```

### 3. Single File Analysis

```bash
pactfix input.py                          # analyze only
pactfix input.py -o output.py             # save fixed file
pactfix input.py --comment -o output.py   # with comments
pactfix input.py --json                   # JSON output
```

### 4. Batch Processing

```bash
pactfix --batch ./src      # analyze directory
pactfix --fix-all          # fix all examples/
```

### 5. Sandbox Setup Only

```bash
pactfix --sandbox-only ./my-project
```

Creates `.pactfix/` with Dockerfile but doesn't analyze/fix files.

### 6. Generate Dockerfiles

```bash
pactfix --init-dockerfiles ./dockerfiles/
```

Creates Dockerfiles for all supported languages.

## Command Reference

| Command | Mode | Modifies Original Files | Creates .pactfix/ |
|---------|------|------------------------|-------------------|
| `--path ./dir --comment` | In-place fix | ✅ Yes | ❌ No |
| `--path ./dir --sandbox` | Sandbox | ❌ No | ✅ Yes |
| `--sandbox-only ./dir` | Setup only | ❌ No | ✅ Yes |
| `input.py -o output.py` | Single file | ❌ No | ❌ No |

## Supported Languages

### Code
- Bash, Python, PHP, JavaScript, Node.js
- TypeScript, Go, Rust, Java, C#, Ruby

### Config Files
- Dockerfile, docker-compose.yml
- SQL, Terraform, Kubernetes YAML
- nginx, GitHub Actions, Ansible
- Apache, Systemd, Makefile

## Sandbox Docker Images

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

## Examples

```bash
# Fix Python project in place with comments
pactfix --path ./my-python-app --comment -v

# Test fixes in Docker sandbox
pactfix --path ./my-node-app --sandbox --test

# Analyze without modifying
pactfix --batch ./src -v
```

## API Server

```bash
python -m pactfix.server
PORT=8000 python -m pactfix.server
```

### Endpoints

- `GET /api/health` - Health check
- `POST /api/analyze` - Analyze code
- `POST /api/detect` - Detect language
- `GET /api/languages` - List supported languages
