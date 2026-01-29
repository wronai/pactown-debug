# Pactfix

[![PyPI version](https://badge.fury.io/py/pactfix.svg)](https://badge.fury.io/py/pactfix)
[![Python versions](https://img.shields.io/pypi/pyversions/pactfix.svg)](https://pypi.org/project/pactfix/)
[![License](https://img.shields.io/pypi/l/pactfix.svg)](https://pypi.org/project/pactfix/)
[![Downloads](https://img.shields.io/pypi/dm/pactfix.svg)](https://pypi.org/project/pactfix/)
[![Tests](https://img.shields.io/badge/tests-202%20passing-green.svg)](https://github.com/wronai/pactown-debug/actions)

> 🔧 **Multi-language code analyzer and auto-fixer with Docker sandbox support**

Pactfix automatically detects and fixes issues in 24+ languages and formats including Bash, Python, Docker, Kubernetes, Terraform, and more. Perfect for code quality, CI/CD pipelines, and development workflows.

## ✨ Key Features

- 🎯 **Auto-fix issues** - Automatically correct common problems
- 🐳 **Docker sandbox** - Test fixes in isolated environments
- 🧪 **Run tests** - Execute tests after applying fixes
- 📦 **Project-wide** - Scan entire codebases at once
- 🔍 **24+ languages** - From Bash to Kubernetes YAML
- 📝 **Detailed reports** - JSON output for CI/CD integration

## 🚀 Quick Install

```bash
pip install pactfix
```

Requires Python 3.10+

## 📖 Basic Usage

### Fix a Single File

```bash
# Analyze only
pactfix script.sh

# Fix and save to new file
pactfix script.sh -o fixed.sh

# Fix with explanatory comments
pactfix script.sh --comment -o fixed.sh
```

### Fix Entire Projects

```bash
# Fix all files in place with comments
pactfix --path ./my-project --comment

# Create fixed copies in .pactfix/ directory
pactfix --path ./my-project
```

### Docker Sandbox Testing

```bash
# Test fixes in Docker container
pactfix --path ./my-project --sandbox

# Test and run tests in container
pactfix --path ./my-project --sandbox --test
```

## 🔧 Language Examples

### Bash/Shell

```bash
# Input
echo "$(ssh user@host cmd") >> file

# Fixed
echo "$(ssh user@host cmd)" >> file  # ✅ Fixed quote position
```

### Python

```python
# Input
def func(items=[]):
    print "hello"

# Fixed
def func(items=None):  # ✅ Avoid mutable defaults
    if items is None:
        items = []
    print("hello")  # ✅ Use print() function
```

### Dockerfile

```dockerfile
# Input
FROM ubuntu:latest
RUN apt-get update
RUN apt-get install python3

# Fixed
FROM ubuntu:22.04  # ✅ Use specific version
RUN apt-get update && apt-get install -y python3 && rm -rf /var/lib/apt/lists/*  # ✅ Combine & cleanup
```

### Docker Compose

```yaml
# Input
services:
  web:
    image: nginx:latest
    privileged: true

# Fixed
services:
  web:
    image: nginx:1.25  # ✅ Versioned image
    # privileged: true  # ✅ Removed for security
```

### Kubernetes

```yaml
# Input
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: app
        image: nginx:latest

# Fixed
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: app
        image: nginx:1.25  # ✅ Versioned image
        resources:  # ✅ Added resource limits
          limits:
            cpu: 500m
            memory: 512Mi
```

### Terraform

```hcl
# Input
resource "aws_instance" "example" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
  access_key    = "AKIAIOSFODNN7EXAMPLE"
}

# Fixed
resource "aws_instance" "example" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
  access_key    = var.access_key  # ✅ Use variable
}

variable "access_key" {
  description = "AWS access key"
  type        = string
  sensitive   = true
}
```

## 🔍 Supported Languages

| Language | Status | Features |
|----------|---------|----------|
| **Bash/Shell** | ✅ Full | Syntax fixes, quoting, error handling |
| **Python** | ✅ Full | Python 3 fixes, best practices |
| **Dockerfile** | ✅ Full | Security, best practices |
| **Docker Compose** | ✅ Full | Version pinning, security |
| **Kubernetes** | ✅ Full | Resource limits, security |
| **Terraform** | ✅ Full | Security, variables, tagging |
| **GitHub Actions** | ✅ Full | Best practices |
| **GitLab CI** | ✅ New | Syntax, best practices |
| **Jenkinsfile** | ✅ New | Declarative pipeline fixes |
| **SQL** | ✅ Full | Syntax, security |
| **Nginx** | ✅ Full | Best practices |
| **Ansible** | ✅ Full | Best practices |
| **And 10+ more** | 🚧 In Progress | Various config formats |

## 📊 CI/CD Integration

### GitHub Actions

```yaml
- name: Run Pactfix
  run: |
    pip install pactfix
    pactfix --path ./src --json > pactfix-report.json
    
- name: Upload Report
  uses: actions/upload-artifact@v3
  with:
    name: pactfix-report
    path: pactfix-report.json
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pactfix
        name: pactfix
        entry: pactfix
        language: system
        args: [--comment]
        types: [text]
```

## 🛠️ Advanced Options

```bash
# Force specific language
pactfix script.py -l python

# Verbose output
pactfix --path ./src --verbose

# JSON output for automation
pactfix script.sh --json

# Batch analyze directory
pactfix --batch ./config

# Generate Dockerfiles
pactfix --init-dockerfiles ./dockerfiles/

# List all supported languages
pactfix --list-languages
```

## 📝 Output Formats

### Console Output

```text
✅ script.sh: 3 errors, 2 warnings, 5 fixes [bash]
❌ Line 5: [SC1073] Misplaced quote
⚠️  Line 10: [SC2086] Unquoted variable
📋 Line 5: Fixed quote position
📋 Line 10: Added quotes around variable
```

### JSON Output

```json
{
  "language": "bash",
  "errors": [
    {
      "line": 5,
      "code": "SC1073",
      "message": "Misplaced quote",
      "severity": "error"
    }
  ],
  "fixes": [
    {
      "line": 5,
      "description": "Fixed quote position",
      "before": "echo \"$(cmd\")",
      "after": "echo \"$(cmd)\""
    }
  ],
  "fixedCode": "..."
}
```

## 🧪 Testing

Pactfix includes comprehensive tests:

```bash
# Run all tests
pytest

# Run specific language tests
pytest tests/test_bash.py

# Run with coverage
pytest --cov=pactfix
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/wronai/pactown-debug/blob/main/CONTRIBUTING.md).

## 📄 License

Apache License 2.0 - see [LICENSE](https://github.com/wronai/pactown-debug/blob/main/LICENSE) for details.

## 🔗 Links

- [Documentation](https://github.com/wronai/pactown-debug/blob/main/pactfix-py/README.md)
- [GitHub Repository](https://github.com/wronai/pactown-debug)
- [Issue Tracker](https://github.com/wronai/pactown-debug/issues)
- [Pactown Platform](https://pactown.dev)

---

**Built with ❤️ by the [Pactown](https://pactown.dev) team**
