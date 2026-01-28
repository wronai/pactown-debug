# pactfix Code Analyzer (Python)

Multi-language code analysis and auto-fix CLI tool.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Analyze and fix a file
pactfix input.py -o output.py

# Analyze with logs
pactfix script.sh --log-file analysis.json

# Force language detection
pactfix code.txt -l python

# JSON output
pactfix input.js --json

# Only analyze, don't write fixed file
pactfix input.php --no-fix
```

## Supported Languages

- **Bash** - ShellCheck-style rules
- **Python** - PEP8 and common issues
- **PHP** - Security and deprecation warnings
- **JavaScript** - ES6+ best practices
- **Node.js** - Server-side specific rules

## Example

```bash
pactfix examples/python/faulty.py -o fixed.py --log-file log.json -v
```

## Output

The tool produces:
1. **Fixed file** - Code with automatic fixes applied
2. **Log file** (optional) - JSON with detailed analysis results
3. **Console output** - Summary of errors, warnings, and fixes
