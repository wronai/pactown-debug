#!/usr/bin/env python3
"""
Pactown Live Debug - Backend Server
Real-time Bash script analysis and auto-fix using ShellCheck
"""

import json
import subprocess
import re
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Common bash fixes - patterns and their corrections
BASH_FIXES = [
    # Misplaced quotes in command substitution
    {
        'pattern': r'echo\s+"(\$\([^)]+)"\)',
        'description': 'Cudzysłów zamykający przed nawiasem - powinien być po nawiasie',
        'fix': lambda m: f'echo "{m.group(1)})"'
    },
    # Missing quotes around variables
    {
        'pattern': r'(\$\{[A-Za-z_][A-Za-z0-9_]*\}|\$[A-Za-z_][A-Za-z0-9_]*)(?=[^"\'}\s])',
        'description': 'Zmienna powinna być w cudzysłowach dla bezpieczeństwa',
    },
    # Using #!/usr/bin/bash instead of #!/bin/bash
    {
        'pattern': r'^#!/usr/bin/bash',
        'description': 'Lepiej użyć #!/bin/bash lub #!/usr/bin/env bash dla przenośności',
    },
    # Missing -r flag in read
    {
        'pattern': r'\bread\s+(?!-r)',
        'description': 'Komenda read powinna używać flagi -r, aby uniknąć interpretacji backslash',
    },
    # cd without || exit
    {
        'pattern': r'^(\s*)cd\s+([^&|;]+)$',
        'description': 'Po cd warto dodać || exit aby obsłużyć błąd zmiany katalogu',
    },
]

# ShellCheck error code mappings with Polish descriptions
SHELLCHECK_MESSAGES = {
    'SC1009': 'Komentarz nie jest dozwolony w tym miejscu',
    'SC1036': 'Brakujący cudzysłów zamykający',
    'SC1073': 'Nie można parsować - brakujący operator lub separator',
    'SC1083': 'Ten znak nie jest cytowany. Użyj cudzysłowów, jeśli ma być literałem',
    'SC2034': 'Ta zmienna wygląda na nieużywaną',
    'SC2086': 'Wartość wymagajaca cytowania (quoting) w celu zabezpieczenia przed word splitting',
    'SC2154': 'Ta zmienna jest używana, ale nie została zdefiniowana',
    'SC2155': 'Deklaracja i przypisanie powinny być rozdzielone',
    'SC2164': 'Użyj cd ... || exit w przypadku niepowodzenia cd',
    'SC2006': 'Użyj $() zamiast przestarzałego ``',
    'SC2046': 'Cytuj zmienną, aby zapobiec word splitting',
    'SC2053': 'Cytuj operand po prawej stronie =~ aby dopasować jako string',
    'SC2059': 'Nie używaj zmiennych w formacie printf - użyj %s',
    'SC2068': 'Cudzysłów tablicowy może zapobiec word splitting',
    'SC2115': 'Użyj "${var:?}" aby zatrzymać, jeśli zmienna jest pusta',
    'SC2162': 'Użyj read -r, aby zapobiec interpretacji backslash',
    'SC2181': 'Sprawdź status wyjścia bezpośrednio, nie przez $?',
}


def run_shellcheck(code: str) -> dict:
    """Run ShellCheck on the code and return parsed results."""
    try:
        # Write code to temp file
        temp_file = '/tmp/shellcheck_input.sh'
        with open(temp_file, 'w') as f:
            f.write(code)
        
        # Run ShellCheck with JSON output
        result = subprocess.run(
            ['shellcheck', '-f', 'json', '-s', 'bash', temp_file],
            capture_output=True,
            text=True
        )
        
        # Parse JSON output
        if result.stdout:
            issues = json.loads(result.stdout)
            return {'success': True, 'issues': issues}
        
        return {'success': True, 'issues': []}
        
    except FileNotFoundError:
        logger.warning("ShellCheck not found, using built-in analysis")
        return {'success': False, 'error': 'ShellCheck not installed'}
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"ShellCheck error: {e}")
        return {'success': False, 'error': str(e)}


def analyze_with_builtin(code: str) -> dict:
    """Built-in analysis when ShellCheck is not available."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check for misplaced quotes in command substitution
        # Pattern: echo "$(command" instead of echo "$(command)"
        match = re.search(r'"\$\([^)]*"\)', line)
        if match:
            errors.append({
                'line': i,
                'column': match.start() + 1,
                'code': 'SC1073',
                'message': 'Cudzysłów zamykający jest w złym miejscu - powinien być po nawiasie )',
                'original': match.group()
            })
            # Create fix
            fixed = re.sub(r'("\$\([^)]*)(")(\))', r'\1\3\2', line)
            if fixed != line:
                fixes.append({
                    'line': i,
                    'message': 'Poprawiono pozycję cudzysłowu zamykającego',
                    'before': line.strip(),
                    'after': fixed.strip()
                })
        
        # Check for unquoted variables
        var_match = re.search(r'(?<!["\'])\$\{?[A-Za-z_][A-Za-z0-9_]*\}?(?!["\'])', line)
        if var_match and not line.strip().startswith('#') and '=' not in line.split('#')[0][:var_match.start()]:
            # Check if it's not already in quotes
            before_var = line[:var_match.start()]
            quote_count = before_var.count('"') - before_var.count('\\"')
            if quote_count % 2 == 0:  # Not inside quotes
                warnings.append({
                    'line': i,
                    'column': var_match.start() + 1,
                    'code': 'SC2086',
                    'message': f'Zmienna {var_match.group()} powinna być w cudzysłowach dla bezpieczeństwa'
                })
        
        # Check for #!/usr/bin/bash
        if i == 1 and stripped.startswith('#!/usr/bin/bash'):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'SC2239',
                'message': 'Rozważ użycie #!/bin/bash lub #!/usr/bin/env bash dla przenośności'
            })
        
        # Check for cd without error handling
        if re.match(r'^\s*cd\s+[^&|;]+$', line) and '||' not in line:
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'SC2164',
                'message': 'Użyj cd ... || exit aby obsłużyć błąd zmiany katalogu'
            })
        
        # Check for read without -r
        if re.search(r'\bread\s+(?!.*-r)', line) and not stripped.startswith('#'):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'SC2162',
                'message': 'Użyj read -r aby zapobiec interpretacji backslash'
            })
    
    return {
        'errors': errors,
        'warnings': warnings,
        'fixes': fixes
    }


def apply_fixes(code: str, issues: list) -> tuple[str, list]:
    """Apply automatic fixes based on ShellCheck issues."""
    lines = code.split('\n')
    fixes = []
    
    for issue in sorted(issues, key=lambda x: (-x.get('line', 0), -x.get('column', 0))):
        line_num = issue.get('line', 0) - 1
        if line_num < 0 or line_num >= len(lines):
            continue
        
        original_line = lines[line_num]
        fixed_line = original_line
        code_id = issue.get('code', '')
        if isinstance(code_id, int):
            code_id = f"SC{code_id}"
        else:
            code_id = str(code_id)
            if code_id and not code_id.startswith('SC'):
                code_id = f"SC{code_id}"
        
        # Apply specific fixes based on error code
        if code_id == 'SC1073' or code_id == 'SC1009':
            # Fix misplaced quotes
            fixed_line = re.sub(r'("\$\([^)]*)(")(\))', r'\1\3\2', original_line)
        
        elif code_id == 'SC2086':
            # Add quotes around variables (careful fix)
            col = issue.get('column', 1) - 1
            end_col = issue.get('endColumn', col + 1)
            if 0 <= col < len(original_line):
                var = original_line[col:end_col] if end_col <= len(original_line) else original_line[col:]
                # Only fix if not already quoted
                if col == 0 or original_line[col-1] != '"':
                    pass  # Skip auto-fix for quoting - it's complex
        
        elif code_id == 'SC2006':
            # Replace backticks with $()
            fixed_line = re.sub(r'`([^`]*)`', r'$(\1)', original_line)
        
        if fixed_line != original_line:
            fixes.append({
                'line': line_num + 1,
                'message': SHELLCHECK_MESSAGES.get(code_id, issue.get('message', 'Poprawiono błąd')),
                'before': original_line.strip(),
                'after': fixed_line.strip()
            })
            lines[line_num] = fixed_line
    
    return '\n'.join(lines), fixes


def analyze_code(code: str) -> dict:
    """Main analysis function combining ShellCheck and built-in checks."""
    result = {
        'originalCode': code,
        'fixedCode': code,
        'errors': [],
        'warnings': [],
        'fixes': []
    }
    
    # Try ShellCheck first
    shellcheck_result = run_shellcheck(code)
    
    if shellcheck_result.get('success') and shellcheck_result.get('issues'):
        issues = shellcheck_result['issues']
        
        # Categorize issues
        for issue in issues:
            level = issue.get('level', 'warning')
            code_id = issue.get('code', '')
            if isinstance(code_id, int):
                code_id = f"SC{code_id}"
            else:
                code_id = str(code_id)
                if code_id and not code_id.startswith('SC'):
                    code_id = f"SC{code_id}"
            msg = {
                'line': issue.get('line', 0),
                'column': issue.get('column', 0),
                'code': code_id,
                'message': SHELLCHECK_MESSAGES.get(code_id, issue.get('message', 'Nieznany błąd'))
            }
            
            if level == 'error':
                result['errors'].append(msg)
            else:
                result['warnings'].append(msg)
        
        # Apply fixes
        fixed_code, fixes = apply_fixes(code, issues)
        result['fixedCode'] = fixed_code
        result['fixes'] = fixes
    
    else:
        # Fallback to built-in analysis
        builtin_result = analyze_with_builtin(code)
        result['errors'] = builtin_result.get('errors', [])
        result['warnings'] = builtin_result.get('warnings', [])
        result['fixes'] = builtin_result.get('fixes', [])
        
        # Apply built-in fixes
        lines = code.split('\n')
        for fix in result['fixes']:
            line_num = fix['line'] - 1
            if 0 <= line_num < len(lines):
                # Find and apply the fix
                if fix['before'] in lines[line_num]:
                    lines[line_num] = lines[line_num].replace(fix['before'], fix['after'])
        
        result['fixedCode'] = '\n'.join(lines)
    
    # Add comments to fixed code
    result['fixedCode'] = add_fix_comments(result['fixedCode'], result['fixes'])
    
    return result


def add_fix_comments(code: str, fixes: list) -> str:
    """Add comments explaining fixes to the code."""
    if not fixes:
        return code
    
    lines = code.split('\n')
    
    # Sort fixes by line number in reverse to avoid offset issues
    for fix in sorted(fixes, key=lambda x: x['line'], reverse=True):
        line_num = fix['line'] - 1
        if 0 <= line_num < len(lines):
            comment = f"  # ✅ NAPRAWIONO: {fix['message']}"
            # Check if line doesn't already have this comment
            if comment not in lines[line_num]:
                lines[line_num] = lines[line_num].rstrip() + comment
    
    return '\n'.join(lines)


def analyze_python_code(code: str) -> dict:
    """Analyze Python code for common issues."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check for print without parentheses (Python 2 style)
        if re.match(r'^print\s+[^(]', stripped):
            errors.append({
                'line': i,
                'column': 1,
                'code': 'PY001',
                'message': 'Użyj print() z nawiasami (Python 3)'
            })
            # Fix: add parentheses
            fixed_line = re.sub(r'^(\s*)print\s+(.+)$', r'\1print(\2)', line)
            if fixed_line != line:
                fixes.append({
                    'line': i,
                    'message': 'Dodano nawiasy do print()',
                    'before': line.strip(),
                    'after': fixed_line.strip()
                })
        
        # Check for bare except
        if re.match(r'^\s*except\s*:', stripped):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'PY002',
                'message': 'Unikaj pustego except: - lepiej użyć except Exception:'
            })
        
        # Check for mutable default arguments
        if re.search(r'def\s+\w+\s*\([^)]*=\s*(\[\]|\{\})', line):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'PY003',
                'message': 'Mutable default argument - może powodować nieoczekiwane zachowanie'
            })
        
        # Check for == None instead of is None
        if re.search(r'==\s*None|!=\s*None', line):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'PY004',
                'message': 'Użyj "is None" lub "is not None" zamiast == None'
            })
        
        # Check for unused imports (simple check)
        if re.match(r'^import\s+(\w+)', stripped):
            module = re.match(r'^import\s+(\w+)', stripped).group(1)
            # Check if module is used elsewhere in code
            module_uses = sum(1 for l in lines if module in l and not l.strip().startswith('import'))
            if module_uses == 0:
                warnings.append({
                    'line': i,
                    'column': 1,
                    'code': 'PY005',
                    'message': f'Import "{module}" może być nieużywany'
                })
        
        # Check for missing docstring in function
        if re.match(r'^\s*def\s+', stripped) and i < len(lines):
            next_line = lines[i].strip() if i < len(lines) else ''
            if next_line and not next_line.startswith(('"""', "'''")):
                warnings.append({
                    'line': i,
                    'column': 1,
                    'code': 'PY006',
                    'message': 'Funkcja nie ma docstringa'
                })
    
    return {
        'errors': errors,
        'warnings': warnings,
        'fixes': fixes
    }


def analyze_php_code(code: str) -> dict:
    """Analyze PHP code for common issues."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check for missing semicolon (simple heuristic)
        if stripped and not stripped.endswith((';', '{', '}', ':', '//', '/*', '*/', '<?php', '?>', '#')) \
           and not stripped.startswith(('if', 'else', 'for', 'while', 'foreach', 'function', 'class', '//', '/*', '*')):
            if '=' in stripped or 'echo' in stripped or 'return' in stripped:
                warnings.append({
                    'line': i,
                    'column': len(stripped),
                    'code': 'PHP001',
                    'message': 'Możliwy brak średnika na końcu linii'
                })
        
        # Check for == instead of === in comparisons
        if re.search(r'[^=!<>]==[^=]', line):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'PHP002',
                'message': 'Użyj === zamiast == dla ścisłego porównania'
            })
        
        # Check for mysql_* functions (deprecated)
        if re.search(r'\bmysql_\w+\s*\(', line):
            errors.append({
                'line': i,
                'column': 1,
                'code': 'PHP003',
                'message': 'Funkcje mysql_* są przestarzałe - użyj mysqli_* lub PDO'
            })
        
        # Check for extract() usage (security risk)
        if re.search(r'\bextract\s*\(', line):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'PHP004',
                'message': 'extract() może być niebezpieczne - rozważ jawne przypisanie'
            })
        
        # Check for error suppression @
        if re.search(r'@\w+', line) and not stripped.startswith('//'):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'PHP005',
                'message': 'Operator @ tłumi błędy - użyj try/catch'
            })
        
        # Check for short open tag
        if '<?=' in line or (stripped.startswith('<?') and not stripped.startswith('<?php')):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'PHP006',
                'message': 'Używaj pełnego tagu <?php zamiast krótkiego <? lub <?='
            })
    
    return {
        'errors': errors,
        'warnings': warnings,
        'fixes': fixes
    }


def analyze_javascript_code(code: str) -> dict:
    """Analyze JavaScript/Node.js code for common issues."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check for var usage (prefer let/const)
        if re.search(r'\bvar\s+\w+', line):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'JS001',
                'message': 'Użyj let lub const zamiast var'
            })
            # Fix: replace var with let
            fixed_line = re.sub(r'\bvar\b', 'let', line)
            if fixed_line != line:
                fixes.append({
                    'line': i,
                    'message': 'Zamieniono var na let',
                    'before': line.strip(),
                    'after': fixed_line.strip()
                })
        
        # Check for == instead of ===
        if re.search(r'[^=!<>]==[^=]', line):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'JS002',
                'message': 'Użyj === zamiast == dla ścisłego porównania'
            })
        
        # Check for console.log (might be debug code)
        if re.search(r'\bconsole\.(log|debug|info)\s*\(', line):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'JS003',
                'message': 'console.log może być kodem debugującym - usuń przed produkcją'
            })
        
        # Check for eval() usage
        if re.search(r'\beval\s*\(', line):
            errors.append({
                'line': i,
                'column': 1,
                'code': 'JS004',
                'message': 'eval() jest niebezpieczne - unikaj użycia'
            })
        
        # Check for function without arrow (in simple cases)
        if re.search(r'function\s*\(\s*\)\s*{', line) and 'constructor' not in line:
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'JS005',
                'message': 'Rozważ użycie arrow function () => {}'
            })
        
        # Check for callback hell (nested callbacks)
        indent = len(line) - len(line.lstrip())
        if indent > 16 and ('function' in line or '=>' in line):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'JS006',
                'message': 'Głębokie zagnieżdżenie - rozważ async/await lub Promise'
            })
        
        # Check for require() vs import (Node.js)
        if re.search(r'\brequire\s*\([\'"]', line):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'NODE001',
                'message': 'Rozważ użycie ES modules (import) zamiast require()'
            })
        
        # Check for sync fs operations in Node.js
        if re.search(r'\b(readFileSync|writeFileSync|appendFileSync)\b', line):
            warnings.append({
                'line': i,
                'column': 1,
                'code': 'NODE002',
                'message': 'Synchroniczne operacje I/O blokują event loop - użyj wersji async'
            })
    
    return {
        'errors': errors,
        'warnings': warnings,
        'fixes': fixes
    }


def detect_language(code: str) -> str:
    """Detect the programming language of the code."""
    lines = code.strip().split('\n')
    first_line = lines[0] if lines else ''
    
    # Check shebang
    if first_line.startswith('#!'):
        if 'python' in first_line.lower():
            return 'python'
        if 'bash' in first_line or 'sh' in first_line:
            return 'bash'
        if 'node' in first_line:
            return 'nodejs'
    
    # Check for PHP
    if '<?php' in code or '<?=' in code:
        return 'php'
    
    # Check for Python-specific patterns
    python_patterns = [
        r'^def\s+\w+\s*\(',
        r'^class\s+\w+.*:',
        r'^import\s+\w+',
        r'^from\s+\w+\s+import',
        r'print\s*\(',
        r'if\s+__name__\s*==',
    ]
    
    for pattern in python_patterns:
        if any(re.search(pattern, line) for line in lines):
            return 'python'
    
    # Check for Node.js-specific patterns
    nodejs_patterns = [
        r'\brequire\s*\([\'"]',
        r'\bmodule\.exports\b',
        r'\bprocess\.(env|argv|exit)\b',
        r'from\s+[\'"][^"\']+[\'"]\s*;?\s*$',
    ]
    
    for pattern in nodejs_patterns:
        if any(re.search(pattern, line) for line in lines):
            return 'nodejs'
    
    # Check for JavaScript patterns
    js_patterns = [
        r'\bconst\s+\w+\s*=',
        r'\blet\s+\w+\s*=',
        r'\bvar\s+\w+\s*=',
        r'function\s+\w+\s*\(',
        r'=>\s*{',
        r'\bdocument\.',
        r'\bwindow\.',
    ]
    
    for pattern in js_patterns:
        if any(re.search(pattern, line) for line in lines):
            return 'javascript'
    
    # Check for Bash-specific patterns
    bash_patterns = [
        r'^\s*for\s+\w+\s+in\s+',
        r'^\s*if\s+\[\s+',
        r'^\s*fi\s*$',
        r'^\s*done\s*$',
        r'\$\{?\w+\}?',
        r'^\s*echo\s+',
    ]
    
    for pattern in bash_patterns:
        if any(re.search(pattern, line) for line in lines):
            return 'bash'
    
    return 'bash'  # Default to bash


def analyze_code_multi(code: str, force_language: str = None) -> dict:
    """Analyze code with automatic language detection."""
    language = force_language or detect_language(code)
    
    result = {
        'originalCode': code,
        'fixedCode': code,
        'errors': [],
        'warnings': [],
        'fixes': [],
        'language': language
    }
    
    lang_result = None
    
    if language == 'python':
        lang_result = analyze_python_code(code)
    elif language == 'php':
        lang_result = analyze_php_code(code)
    elif language in ('javascript', 'nodejs'):
        lang_result = analyze_javascript_code(code)
    else:
        # Use existing bash analysis
        bash_result = analyze_code(code)
        result['errors'] = bash_result.get('errors', [])
        result['warnings'] = bash_result.get('warnings', [])
        result['fixes'] = bash_result.get('fixes', [])
        result['fixedCode'] = bash_result.get('fixedCode', code)
        return result
    
    if lang_result:
        result['errors'] = lang_result.get('errors', [])
        result['warnings'] = lang_result.get('warnings', [])
        result['fixes'] = lang_result.get('fixes', [])
        
        # Apply fixes
        lines = code.split('\n')
        for fix in result['fixes']:
            line_num = fix['line'] - 1
            if 0 <= line_num < len(lines):
                if fix['before'] in lines[line_num]:
                    lines[line_num] = lines[line_num].replace(fix['before'], fix['after'])
        
        result['fixedCode'] = '\n'.join(lines)
        
        # Add comments based on language
        comment_char = '#' if language == 'python' else '//'
        result['fixedCode'] = add_fix_comments_lang(result['fixedCode'], result['fixes'], comment_char)
    
    return result


def add_fix_comments_lang(code: str, fixes: list, comment_char: str = '#') -> str:
    """Add comments explaining fixes to the code with language-specific comment style."""
    if not fixes:
        return code
    
    lines = code.split('\n')
    
    for fix in sorted(fixes, key=lambda x: x['line'], reverse=True):
        line_num = fix['line'] - 1
        if 0 <= line_num < len(lines):
            comment = f"  {comment_char} ✅ NAPRAWIONO: {fix['message']}"
            if comment not in lines[line_num]:
                lines[line_num] = lines[line_num].rstrip() + comment
    
    return '\n'.join(lines)


class DebugHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the debug server."""
    
    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory or '/app'
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Check ShellCheck availability
            shellcheck_available = subprocess.run(
                ['which', 'shellcheck'], capture_output=True
            ).returncode == 0
            
            health = {
                'status': 'healthy',
                'version': '1.1.0',
                'features': {
                    'shellcheck': shellcheck_available,
                    'bash_analysis': True,
                    'python_analysis': True,
                    'auto_fix': True
                }
            }
            self.wfile.write(json.dumps(health).encode())
        else:
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests for code analysis."""
        if self.path == '/api/analyze':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
                code = data.get('code', '')
                
                logger.info(f"Analyzing code ({len(code)} chars)")
                result = analyze_code_multi(code)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except json.JSONDecodeError as e:
                self.send_error(400, f'Invalid JSON: {e}')
            except Exception as e:
                logger.error(f"Analysis error: {e}")
                self.send_error(500, str(e))
        else:
            self.send_error(404, 'Not Found')
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom logging."""
        logger.info(f"{self.address_string()} - {format % args}")


def main():
    """Start the debug server."""
    port = int(os.environ.get('PORT', 8080))
    server_address = ('', port)
    
    # Set directory
    app_dir_env = os.environ.get('APP_DIR')
    if app_dir_env:
        app_dir = app_dir_env
    else:
        local_app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
        app_dir = local_app_dir if os.path.isdir(local_app_dir) else '/app'
    
    handler = lambda *args, **kwargs: DebugHandler(*args, directory=app_dir, **kwargs)
    httpd = HTTPServer(server_address, handler)
    
    logger.info(f"🚀 Pactown Live Debug Server starting on port {port}")
    logger.info(f"📂 Serving files from {app_dir}")
    logger.info(f"🔍 ShellCheck integration: {'enabled' if subprocess.run(['which', 'shellcheck'], capture_output=True).returncode == 0 else 'using fallback'}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        httpd.shutdown()


if __name__ == '__main__':
    main()
