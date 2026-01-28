"""
pactfix Code Analyzer - Core Analysis Engine
Analyzes code files for common issues across multiple languages.
"""

import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Issue:
    line: int
    column: int
    code: str
    message: str
    severity: str = "warning"


@dataclass
class Fix:
    line: int
    message: str
    before: str
    after: str


@dataclass
class AnalysisResult:
    original_code: str
    fixed_code: str
    language: str
    errors: List[Issue]
    warnings: List[Issue]
    fixes: List[Fix]
    timestamp: str
    
    def to_dict(self) -> dict:
        return {
            "originalCode": self.original_code,
            "fixedCode": self.fixed_code,
            "language": self.language,
            "errors": [asdict(e) for e in self.errors],
            "warnings": [asdict(w) for w in self.warnings],
            "fixes": [asdict(f) for f in self.fixes],
            "timestamp": self.timestamp
        }


def detect_language(code: str, filename: str = None) -> str:
    """Detect the programming language of the code."""
    if filename:
        ext = Path(filename).suffix.lower()
        ext_map = {
            '.py': 'python',
            '.sh': 'bash',
            '.bash': 'bash',
            '.php': 'php',
            '.js': 'javascript',
            '.mjs': 'javascript',
            '.cjs': 'nodejs',
        }
        if ext in ext_map:
            return ext_map[ext]
    
    lines = code.strip().split('\n')
    first_line = lines[0] if lines else ''
    
    if first_line.startswith('#!'):
        if 'python' in first_line.lower():
            return 'python'
        if 'bash' in first_line or 'sh' in first_line:
            return 'bash'
        if 'node' in first_line:
            return 'nodejs'
    
    if '<?php' in code or '<?=' in code:
        return 'php'
    
    python_patterns = [r'^def\s+\w+\s*\(', r'^class\s+\w+', r'^import\s+\w+', r'^from\s+\w+\s+import']
    for pattern in python_patterns:
        if any(re.search(pattern, line) for line in lines):
            return 'python'
    
    nodejs_patterns = [r'\brequire\s*\([\'"]', r'\bmodule\.exports\b', r'\bprocess\.(env|argv)\b']
    for pattern in nodejs_patterns:
        if any(re.search(pattern, line) for line in lines):
            return 'nodejs'
    
    js_patterns = [r'\bconst\s+\w+\s*=', r'\blet\s+\w+\s*=', r'\bvar\s+\w+\s*=', r'=>\s*{']
    for pattern in js_patterns:
        if any(re.search(pattern, line) for line in lines):
            return 'javascript'
    
    bash_patterns = [r'^\s*for\s+\w+\s+in\s+', r'^\s*if\s+\[\s+', r'\$\{?\w+\}?']
    for pattern in bash_patterns:
        if any(re.search(pattern, line) for line in lines):
            return 'bash'
    
    return 'bash'


def analyze_bash(code: str) -> tuple[List[Issue], List[Issue], List[Fix]]:
    """Analyze Bash code."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Misplaced quotes in command substitution
        if re.search(r'"\$\([^)]*"\)', line):
            errors.append(Issue(i, 1, 'SC1073', 'Cudzysłów zamykający jest w złym miejscu'))
            fixed = re.sub(r'("\$\([^)]*)(")(\))', r'\1\3\2', line)
            if fixed != line:
                fixes.append(Fix(i, 'Poprawiono pozycję cudzysłowu', line.strip(), fixed.strip()))
        
        # cd without error handling
        if re.match(r'^\s*cd\s+[^&|;]+$', line) and '||' not in line:
            warnings.append(Issue(i, 1, 'SC2164', 'Użyj cd ... || exit'))
        
        # read without -r
        if re.search(r'\bread\s+(?!.*-r)', line) and not stripped.startswith('#'):
            warnings.append(Issue(i, 1, 'SC2162', 'Użyj read -r'))
    
    return errors, warnings, fixes


def analyze_python(code: str) -> tuple[List[Issue], List[Issue], List[Fix]]:
    """Analyze Python code."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if re.match(r'^print\s+[^(]', stripped):
            errors.append(Issue(i, 1, 'PY001', 'Użyj print() z nawiasami (Python 3)'))
            fixed = re.sub(r'^(\s*)print\s+(.+)$', r'\1print(\2)', line)
            if fixed != line:
                fixes.append(Fix(i, 'Dodano nawiasy do print()', line.strip(), fixed.strip()))
        
        if re.match(r'^\s*except\s*:', stripped):
            warnings.append(Issue(i, 1, 'PY002', 'Unikaj pustego except:'))
        
        if re.search(r'def\s+\w+\s*\([^)]*=\s*(\[\]|\{\})', line):
            warnings.append(Issue(i, 1, 'PY003', 'Mutable default argument'))
        
        if re.search(r'==\s*None|!=\s*None', line):
            warnings.append(Issue(i, 1, 'PY004', 'Użyj "is None" zamiast == None'))
    
    return errors, warnings, fixes


def analyze_php(code: str) -> tuple[List[Issue], List[Issue], List[Fix]]:
    """Analyze PHP code."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if re.search(r'[^=!<>]==[^=]', line):
            warnings.append(Issue(i, 1, 'PHP002', 'Użyj === zamiast =='))
        
        if re.search(r'\bmysql_\w+\s*\(', line):
            errors.append(Issue(i, 1, 'PHP003', 'Funkcje mysql_* są przestarzałe'))
        
        if re.search(r'\bextract\s*\(', line):
            warnings.append(Issue(i, 1, 'PHP004', 'extract() może być niebezpieczne'))
        
        if re.search(r'@\w+', line) and not stripped.startswith('//'):
            warnings.append(Issue(i, 1, 'PHP005', 'Operator @ tłumi błędy'))
        
        if '<?=' in line or (stripped.startswith('<?') and not stripped.startswith('<?php')):
            warnings.append(Issue(i, 1, 'PHP006', 'Używaj pełnego tagu <?php'))
    
    return errors, warnings, fixes


def analyze_javascript(code: str) -> tuple[List[Issue], List[Issue], List[Fix]]:
    """Analyze JavaScript/Node.js code."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if re.search(r'\bvar\s+\w+', line):
            warnings.append(Issue(i, 1, 'JS001', 'Użyj let lub const zamiast var'))
            fixed = re.sub(r'\bvar\b', 'let', line)
            if fixed != line:
                fixes.append(Fix(i, 'Zamieniono var na let', line.strip(), fixed.strip()))
        
        if re.search(r'[^=!<>]==[^=]', line):
            warnings.append(Issue(i, 1, 'JS002', 'Użyj === zamiast =='))
        
        if re.search(r'\bconsole\.(log|debug|info)\s*\(', line):
            warnings.append(Issue(i, 1, 'JS003', 'console.log - usuń przed produkcją'))
        
        if re.search(r'\beval\s*\(', line):
            errors.append(Issue(i, 1, 'JS004', 'eval() jest niebezpieczne'))
        
        if re.search(r'\brequire\s*\([\'"]', line):
            warnings.append(Issue(i, 1, 'NODE001', 'Rozważ ES modules zamiast require()'))
        
        if re.search(r'\b(readFileSync|writeFileSync)\b', line):
            warnings.append(Issue(i, 1, 'NODE002', 'Synchroniczne I/O blokuje event loop'))
    
    return errors, warnings, fixes


def apply_fixes(code: str, fixes: List[Fix], language: str) -> str:
    """Apply fixes to the code and add comments."""
    lines = code.split('\n')
    comment_char = '#' if language in ('python', 'bash') else '//'
    
    for fix in fixes:
        line_num = fix.line - 1
        if 0 <= line_num < len(lines):
            if fix.before in lines[line_num]:
                lines[line_num] = lines[line_num].replace(fix.before, fix.after)
    
    for fix in sorted(fixes, key=lambda x: x.line, reverse=True):
        line_num = fix.line - 1
        if 0 <= line_num < len(lines):
            comment = f"  {comment_char} ✅ NAPRAWIONO: {fix.message}"
            if comment not in lines[line_num]:
                lines[line_num] = lines[line_num].rstrip() + comment
    
    return '\n'.join(lines)


def analyze_code(code: str, language: str = None, filename: str = None) -> AnalysisResult:
    """Analyze code and return results."""
    lang = language or detect_language(code, filename)
    
    analyzers = {
        'bash': analyze_bash,
        'python': analyze_python,
        'php': analyze_php,
        'javascript': analyze_javascript,
        'nodejs': analyze_javascript,
    }
    
    analyzer = analyzers.get(lang, analyze_bash)
    errors, warnings, fixes = analyzer(code)
    
    fixed_code = apply_fixes(code, fixes, lang)
    
    return AnalysisResult(
        original_code=code,
        fixed_code=fixed_code,
        language=lang,
        errors=errors,
        warnings=warnings,
        fixes=fixes,
        timestamp=datetime.now().isoformat()
    )


def analyze_file(input_path: str, output_path: str = None, language: str = None) -> AnalysisResult:
    """Analyze a file and optionally write the fixed version."""
    path = Path(input_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")
    
    code = path.read_text(encoding='utf-8')
    result = analyze_code(code, language, str(path))
    
    if output_path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result.fixed_code, encoding='utf-8')
    
    return result
