# Pactown Live Debug - Raport rozwoju

## Wersja 1.1.0 (2026-01-28)

### Nowe funkcjonalności

#### 1. Wsparcie dla Python
- **Automatyczna detekcja języka** - system rozpoznaje czy kod to Bash czy Python
- **Analiza kodu Python** z wykrywaniem typowych błędów:
  - `PY001` - print bez nawiasów (Python 2 style)
  - `PY002` - puste except:
  - `PY003` - mutable default arguments
  - `PY004` - == None zamiast is None
  - `PY005` - nieużywane importy
  - `PY006` - brak docstringa w funkcji
- **Przykładowy kod Python** - nowy przycisk "🐍 Python" w UI

#### 2. API Health Check
- Nowy endpoint `GET /api/health` zwracający:
  - Status serwera
  - Wersję aplikacji
  - Dostępne funkcje (shellcheck, bash_analysis, python_analysis, auto_fix)

#### 3. Testy E2E z Playwright
- **22 testy end-to-end** pokrywające:
  - Ładowanie aplikacji
  - Analiza kodu Bash i Python
  - Kopiowanie i pobieranie wyników
  - Historia zmian
  - API endpoints
  - Podświetlanie składni

### Uruchomienie testów

```bash
# Instalacja zależności
npm install

# Uruchomienie testów
npm test

# Testy z interfejsem graficznym
npm run test:ui

# Testy w trybie headed (widoczna przeglądarka)
npm run test:headed
```

### Struktura testów

```
e2e/
└── app.spec.ts          # Główny plik testów
    ├── Pactown Live Debug - E2E Tests (12 testów)
    ├── Python Analysis Tests (3 testy)
    └── API Tests (7 testów)
```

### Roadmap - pozostałe do zrealizowania

- [ ] AI-powered explanations (llama.cpp)
- [ ] Collaborative debugging
- [ ] VSCode extension
- [x] ~~Wsparcie dla Python~~ ✅
- [ ] Wsparcie dla Node.js

---

*Raport wygenerowany automatycznie podczas sesji rozwojowej*



# Comprehensive live debugging and auto-fix for embedded scripts

**The optimal stack for pre-execution code analysis combines Ruff for Python (10-100x faster than alternatives), ShellCheck with JSON output for Bash, and ESLint or Biome for JavaScript**—all invoked programmatically via subprocess with structured JSON responses. For errors that static tools cannot fix, LLM-assisted repair using Aider or the Instructor library provides structured fallback with validation pipelines. The key insight is that **no single tool provides native programmatic APIs across all languages**, so the most effective architecture uses subprocess orchestration with unified SARIF output, enabling parallel execution via asyncio and containerization with pre-warmed Alpine-based images.

---

## Python tools form the most mature ecosystem for programmatic linting

Ruff has emerged as the dominant Python linter, achieving **0.4 seconds on 250,000 lines of code** compared to Pylint's 2.5 minutes on the same codebase. Written in Rust, Ruff consolidates the functionality of Flake8, Black, isort, pydocstyle, pyupgrade, and autoflake into a single binary with **800+ built-in rules**. The `--output-format=json` flag produces structured output with line numbers, column positions, and crucially, the `fix` field containing exact text replacements:

```json
{
  "code": "F401",
  "message": "unused import",
  "location": {"row": 1, "column": 1},
  "fix": {"applicability": "safe", "edits": [{"content": "", "location": {...}}]}
}
```

Ruff distinguishes between **safe fixes** (preserving semantics) and **unsafe fixes** (potentially changing behavior). Running `ruff check --fix` applies only safe fixes by default, while `--unsafe-fixes` enables all corrections. This distinction is critical for automated pipelines where false positives could introduce bugs.

Despite Ruff's speed, it lacks a native Python API—all invocations require subprocess calls or stdin/stdout communication. For programmatic control, Python's built-in `ast.parse()` provides **instant syntax validation** with detailed error information including line numbers, column offsets, and the problematic text itself. When syntax errors exist, no linter can proceed, making ast.parse() the essential first step.

For code transformation beyond what Ruff offers, **LibCST preserves whitespace and comments** while enabling AST manipulation. Unlike Python's ast module, LibCST maintains concrete syntax tree information, making it suitable for codemods that must preserve formatting:

```python
import libcst as cst
tree = cst.parse_module(source_code)
modified_tree = tree.visit(RemoveUnusedImportsTransformer())
fixed_code = modified_tree.code
```

Type checking requires Pyright or mypy. Pyright runs **5-10x faster than mypy** and outputs JSON via `pyright --outputjson`. For continuous development, mypy's daemon mode (`dmypy`) maintains type checker state in memory, enabling sub-second incremental checks after the initial analysis.

---

## ShellCheck provides structured fix suggestions for Bash scripts

ShellCheck remains the definitive static analyzer for shell scripts, detecting **hundreds of error patterns** from quoting issues to non-POSIX constructs. The modern `json1` format includes machine-readable fix suggestions:

```bash
shellcheck -f json1 -s bash script.sh
```

Each diagnostic includes `line`, `column`, `endLine`, `endColumn` positions, severity levels (`error`, `warning`, `info`, `style`), and importantly, a `fix` object containing `replacements` with exact insertion points. **SC2086 (unquoted variables)** appears most frequently; ShellCheck provides the exact quotes needed to fix it.

The `diff` output format generates patches directly applicable via `patch -p1` or `git apply`:

```bash
shellcheck -f diff script.sh | patch -p1
```

For comprehensive hardening, **shellharden focuses specifically on quoting**, using `--transform` to output corrected scripts or `--replace` for in-place modification. Combined with **shfmt for formatting** (2-space indents, case statement indentation), a complete Bash lint-fix pipeline emerges:

```python
# Pipeline: shellharden for quoting → shfmt for formatting → shellcheck for verification
subprocess.run(['shellharden', '--transform', '-'], input=code, capture_output=True)
subprocess.run(['shfmt', '-i', '2', '-ci', '-'], input=hardened, capture_output=True)
subprocess.run(['shellcheck', '-f', 'json1', '-'], input=formatted, capture_output=True)
```

ShellCheck has no Python bindings—it's written in Haskell. Container images like `koalaman/shellcheck:stable` provide **16MB minimal images** for CI environments.

---

## JavaScript linting offers the richest programmatic APIs

ESLint provides the most mature programmatic interface through its Node.js API. The `ESLint` class exposes `lintFiles()` and `lintText()` methods with full auto-fix support:

```javascript
const { ESLint } = require("eslint");
const eslint = new ESLint({ fix: true });
const results = await eslint.lintText(code, { filePath: "virtual.js" });
await ESLint.outputFixes(results);
```

Each `LintResult` contains `messages` with `line`, `column`, `ruleId`, `message`, and critically, a `fix` object with `range` and replacement `text`. The **flat config format (eslint.config.js)** became default in ESLint v9.0.0, simplifying configuration with explicit imports.

For raw speed, **Biome (Rome's successor) runs 10-25x faster than ESLint** while combining linting and formatting. Biome v2.0 introduced type inference capabilities and now supports 425+ rules. Oxlint from VoidZero pushes further with **50-100x speedups**—linting 264,925 files in 22.5 seconds.

Syntax error detection before linting uses `@babel/parser` with `errorRecovery: true` for detailed diagnostics or Prettier's `format()` which throws `SyntaxError` on invalid code. TypeScript's compiler API enables programmatic type checking even for JavaScript files via `allowJs` and `checkJs` options:

```javascript
const program = ts.createProgram(["app.js"], { allowJs: true, checkJs: true });
const diagnostics = ts.getPreEmitDiagnostics(program);
```

---

## Mocking systems enable isolated execution in containers

For Python HTTP mocking, **responses** handles the requests library while **respx** covers httpx/async code. Both use decorators that intercept network calls:

```python
@responses.activate
def test_api():
    responses.add(responses.GET, "http://api.example.com/", json={"data": "mocked"})
    response = requests.get("http://api.example.com/")
```

**VCRpy implements the recording/replay pattern**, storing HTTP interactions as YAML cassettes for deterministic tests. Key configurations include `filter_query_parameters` to redact API keys and `decode_compressed_response` for readable cassettes.

Bash mocking requires **bats-mock** with its `stub` command that creates executables returning predefined output:

```bash
stub terraform "init -input=false : echo 'init called'" "plan : echo 'plan called'"
run my_script.sh
unstub terraform
```

For JavaScript, **nock** now uses MSW's interceptors internally, providing consistent mocking across Node.js versions. **MSW (Mock Service Worker)** works identically in browsers and Node.js, making it ideal for isomorphic applications.

Container-level HTTP mocking uses **WireMock** as a sidecar container with JSON stub files:

```yaml
services:
  app:
    environment:
      - API_URL=http://wiremock:8080
  wiremock:
    image: wiremock/wiremock
    volumes:
      - ./stubs:/home/wiremock/mappings
```

For traffic inspection without stub files, **mitmproxy** intercepts all HTTP traffic, enabling response modification via Python addons.

---

## Unified pipelines aggregate linters with parallel execution

**MegaLinter** orchestrates 50+ linters across languages with Docker-based execution, SARIF output, and parallel processing. Configuration specifies enabled linters and auto-fix behavior:

```yaml
ENABLE_LINTERS: [PYTHON_RUFF, PYTHON_MYPY, JAVASCRIPT_ES, BASH_SHELLCHECK]
APPLY_FIXES: all
SARIF_REPORTER: true
```

For custom pipelines, **asyncio.subprocess** enables concurrent linter execution:

```python
async def parallel_lint(files):
    tasks = [
        run_linter(["ruff", "check", "--output-format=json"] + files, "ruff"),
        run_linter(["eslint", "--format=json"] + files, "eslint"),
        run_linter(["shellcheck", "-f", "json1"] + files, "shellcheck")
    ]
    return await asyncio.gather(*tasks)
```

**SARIF (Static Analysis Results Interchange Format)** provides a standardized schema for lint results. Ruff, ESLint (via `@microsoft/eslint-formatter-sarif`), and MegaLinter all support SARIF output, enabling unified processing regardless of source linter.

The Language Server Protocol offers real-time diagnostics with fix suggestions. The `textDocument/codeAction` request returns `CodeAction` objects containing `WorkspaceEdit` with exact text changes. VSCode's "Fix All" feature sends this request with `only: ["source.fixAll"]`, applying all returned edits sequentially.

---

## Container optimization reduces lint startup to milliseconds

**Alpine-based multi-stage builds** minimize image size while pre-warming caches:

```dockerfile
FROM python:3.12-slim AS builder
RUN pip install --user ruff mypy

FROM python:3.12-alpine AS runtime
COPY --from=builder /root/.local /root/.local
RUN ruff --version  # Pre-warm cache
```

Ruff's cold start is approximately **50ms** compared to Pylint's 2-3 seconds. Using `docker exec` against running containers reduces startup to **50-100ms** versus 500ms-2s for `docker run`.

Volume-mounted caches persist analysis results across container invocations:

```bash
docker run -v $(pwd)/.ruff_cache:/app/.ruff_cache \
           -v $(pwd)/.mypy_cache:/app/.mypy_cache \
           linter-image
```

ESLint caching (`--cache --cache-location .eslintcache`) combined with ESLint v9.34's `--concurrency` flag enables **multi-threaded linting**. Ruff caches automatically to `.ruff_cache/`.

---

## LLM fallback handles semantic errors beyond rule-based fixes

Static tools excel at formatting, import sorting, and pattern-matched errors. **LLMs are necessary for logic bugs, complex refactoring, and context-dependent fixes** where understanding intent matters.

**Aider** provides the most robust CLI-based code repair, using tree-sitter for codebase context and SEARCH/REPLACE blocks for precise edits:

```bash
aider --model sonnet --message "fix the type error on line 42" --file src/main.py
```

For programmatic LLM integration, **Instructor with Pydantic** guarantees structured JSON output:

```python
from instructor import from_openai
from pydantic import BaseModel

class CodeFix(BaseModel):
    original_line: str
    fixed_line: str
    explanation: str

client = from_openai(OpenAI())
fix = client.chat.completions.create(
    model="gpt-4o",
    response_model=CodeFix,
    messages=[{"role": "user", "content": f"Fix: {error}\nCode: {code}"}]
)
```

**DeepSeek-Coder-V2** offers the best local model performance, requiring **40% fewer corrections than CodeLlama**. Running via Ollama enables privacy-critical deployments with sub-second latency.

The fallback chain should route through static fixes first, then LLM:

1. Run linter with `--fix` for safe automatic corrections
2. Filter remaining unfixable errors
3. Batch similar errors and send to LLM
4. Validate LLM fixes with `ast.parse()` and re-linting
5. Detect hallucinations (new imports that don't exist, suspicious function calls)

Cost optimization uses fast models (GPT-4o-mini, Claude Haiku at **$0.0001-0.0008 per 1K tokens**) for simple fixes and stronger models for complex multi-file changes.

---

## Generating inline comments explaining fixes

The output format for a live debugging system should include the original code, fixed code, and explanations. A unified schema:

```python
@dataclass
class FixAnnotation:
    file: str
    line: int
    original: str
    fixed: str
    error_type: str
    explanation: str
    fix_source: Literal["ruff", "shellcheck", "eslint", "llm"]
```

For inline comments, LLM prompts should request the format explicitly:

```
Fix this code and add inline comments explaining each change:
// FIX: [explanation of what was changed and why]
```

Diff-style output uses unified diff format, applicable via `patch`:

```diff
--- a/script.py
+++ b/script.py
@@ -10,1 +10,2 @@
-    return sum(numbers) / len(numbers)
+    if not numbers:
+        return 0.0  # FIX: Handle empty list to prevent division by zero
+    return sum(numbers) / len(numbers)
```

---

## Recommended architecture for Markdown-embedded scripts

The complete system extracts code blocks from Markdown, routes to language-specific linters, applies fixes, and re-embeds corrected code with annotations:

- **Extraction**: Parse Markdown fenced code blocks with language identifiers
- **Routing**: Python → Ruff + ast.parse(); Bash → ShellCheck + shellharden; JavaScript → ESLint/Biome
- **Orchestration**: asyncio.subprocess for parallel execution across languages
- **Output aggregation**: SARIF format for unified result handling
- **LLM fallback**: Instructor-wrapped API calls for semantic fixes
- **Validation**: Re-lint all LLM fixes, syntax check, detect hallucinations
- **Re-embedding**: Insert fixed code with inline comments into original Markdown

Tool versions as of January 2026: **Ruff v0.14.x**, **ShellCheck v0.10.x**, **ESLint v9.34.x**, **Biome v2.0**, **Oxlint v1.0**. MegaLinter and pre-commit provide turnkey multi-language pipelines. For custom orchestration, asyncio with JSON output parsing offers maximum flexibility with minimal overhead in containerized environments.