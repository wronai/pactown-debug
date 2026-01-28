# Pactown Code Analyzer (Node.js)

Multi-language code analysis and auto-fix CLI tool.

## Installation

```bash
npm install
npm link  # For global CLI access
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

# Verbose output
pactfix app.js -v
```

## Supported Languages

- **Bash** - ShellCheck-style rules
- **Python** - PEP8 and common issues
- **PHP** - Security and deprecation warnings
- **JavaScript** - ES6+ best practices
- **Node.js** - Server-side specific rules

## Programmatic Usage

```javascript
import { analyzeFile, analyzeCode } from 'pactfix';

// Analyze a file
const result = analyzeFile('input.py', 'output.py');

// Analyze code string
const result2 = analyzeCode('var x = 1;', 'javascript');

console.log(result.errors);
console.log(result.warnings);
console.log(result.fixes);
```

## Output

The tool produces:

1. **Fixed file** - Code with automatic fixes applied
2. **Log file** (optional) - JSON with detailed analysis results
3. **Console output** - Summary of errors, warnings, and fixes
