#!/usr/bin/env python3
"""
Pactown Live Debug - Backend Server
Real-time Bash script analysis and auto-fix using ShellCheck
"""

import json
import subprocess
import re
import os
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import logging

PACTFIX_API_URL = os.environ.get('PACTFIX_API_URL', '')

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


def analyze_dockerfile(code: str) -> dict:
    """Analyze Dockerfile for common issues and best practices."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    has_user = False
    has_healthcheck = False
    last_cmd_line = 0
    base_image = None
    env_vars = set()
    exposed_ports = set()
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        upper_line = stripped.upper()
        
        # Extract context
        if upper_line.startswith('FROM '):
            base_image = stripped[5:].strip().split()[0]
            if ':latest' in base_image or (':' not in base_image and '@' not in base_image):
                warnings.append({
                    'line': i, 'column': 1, 'code': 'DOCKER001',
                    'message': f'Użyj konkretnego tagu zamiast :latest dla obrazu {base_image}'
                })
        
        if upper_line.startswith('USER '):
            has_user = True
        
        if upper_line.startswith('HEALTHCHECK '):
            has_healthcheck = True
        
        if upper_line.startswith('ENV '):
            parts = stripped[4:].split('=')
            if parts:
                env_vars.add(parts[0].strip())
        
        if upper_line.startswith('EXPOSE '):
            ports = stripped[7:].split()
            exposed_ports.update(ports)
        
        # Check for RUN with apt-get without cleanup
        if upper_line.startswith('RUN ') and 'apt-get install' in stripped:
            if 'rm -rf /var/lib/apt/lists' not in stripped and '&&' not in stripped:
                warnings.append({
                    'line': i, 'column': 1, 'code': 'DOCKER002',
                    'message': 'apt-get install bez czyszczenia cache - dodaj && rm -rf /var/lib/apt/lists/*'
                })
            if 'apt-get update' not in stripped:
                warnings.append({
                    'line': i, 'column': 1, 'code': 'DOCKER003',
                    'message': 'apt-get install bez apt-get update w tej samej warstwie'
                })
        
        # Check for ADD vs COPY
        if upper_line.startswith('ADD ') and 'http' not in stripped and '.tar' not in stripped:
            warnings.append({
                'line': i, 'column': 1, 'code': 'DOCKER004',
                'message': 'Użyj COPY zamiast ADD dla lokalnych plików (ADD ma dodatkowe funkcje)'
            })
        
        # Check for COPY with --chown
        if upper_line.startswith('COPY ') and '--chown' not in stripped and has_user:
            warnings.append({
                'line': i, 'column': 1, 'code': 'DOCKER005',
                'message': 'Rozważ użycie COPY --chown=user:group dla poprawnych uprawnień'
            })
        
        # Check for CMD/ENTRYPOINT format
        if upper_line.startswith('CMD ') or upper_line.startswith('ENTRYPOINT '):
            last_cmd_line = i
            if not stripped.endswith(']') and '[' not in stripped:
                warnings.append({
                    'line': i, 'column': 1, 'code': 'DOCKER006',
                    'message': 'Użyj formy exec (JSON array) zamiast shell form dla CMD/ENTRYPOINT'
                })
        
        # Check for hardcoded secrets
        secret_patterns = ['PASSWORD=', 'SECRET=', 'API_KEY=', 'TOKEN=', 'PRIVATE_KEY']
        for pattern in secret_patterns:
            if pattern in upper_line and 'ARG' not in upper_line:
                errors.append({
                    'line': i, 'column': 1, 'code': 'DOCKER007',
                    'message': f'Możliwy hardcoded secret - użyj build args lub secrets'
                })
        
        # Check for WORKDIR with relative path
        if upper_line.startswith('WORKDIR ') and not stripped[8:].strip().startswith('/'):
            warnings.append({
                'line': i, 'column': 1, 'code': 'DOCKER008',
                'message': 'WORKDIR powinien używać ścieżki absolutnej'
            })
    
    # Context-based warnings
    if not has_user:
        warnings.append({
            'line': 1, 'column': 1, 'code': 'DOCKER009',
            'message': 'Brak instrukcji USER - kontener będzie działał jako root'
        })
    
    if not has_healthcheck and base_image:
        warnings.append({
            'line': 1, 'column': 1, 'code': 'DOCKER010',
            'message': 'Brak HEALTHCHECK - dodaj dla lepszego monitorowania kontenera'
        })
    
    return {'errors': errors, 'warnings': warnings, 'fixes': fixes, 
            'context': {'base_image': base_image, 'env_vars': list(env_vars), 'exposed_ports': list(exposed_ports)}}


def analyze_docker_compose(code: str) -> dict:
    """Analyze docker-compose.yml for common issues."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    services = []
    current_service = None
    current_indent = 0
    has_networks = False
    has_volumes_def = False
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        
        # Track services
        if stripped.startswith('services:'):
            continue
        if indent == 2 and stripped.endswith(':') and not stripped.startswith('-'):
            current_service = stripped[:-1]
            services.append(current_service)
        
        if 'networks:' in stripped and indent == 0:
            has_networks = True
        if stripped == 'volumes:' and indent == 0:
            has_volumes_def = True
        
        # Check for latest tag
        if 'image:' in stripped and (':latest' in stripped or (':' not in stripped.split('image:')[1])):
            warnings.append({
                'line': i, 'column': 1, 'code': 'COMPOSE001',
                'message': 'Użyj konkretnego tagu wersji zamiast :latest'
            })
        
        # Check for privileged mode
        if 'privileged: true' in stripped:
            errors.append({
                'line': i, 'column': 1, 'code': 'COMPOSE002',
                'message': 'privileged: true jest niebezpieczne - ogranicz capabilities'
            })
        
        # Check for host network mode
        if 'network_mode: host' in stripped:
            warnings.append({
                'line': i, 'column': 1, 'code': 'COMPOSE003',
                'message': 'network_mode: host omija izolację sieciową Dockera'
            })
        
        # Check for bind mounts without read-only
        if ':rw' in stripped or (stripped.startswith('- ') and ':/' in stripped and ':ro' not in stripped):
            if '/var/run/docker.sock' in stripped:
                errors.append({
                    'line': i, 'column': 1, 'code': 'COMPOSE004',
                    'message': 'Montowanie docker.sock daje pełny dostęp do Docker daemon'
                })
        
        # Check for hardcoded secrets in environment
        if 'environment:' in stripped or (stripped.startswith('- ') and '=' in stripped):
            secret_patterns = ['PASSWORD=', 'SECRET=', 'API_KEY=', 'TOKEN=']
            for pattern in secret_patterns:
                if pattern in stripped.upper() and '${' not in stripped:
                    errors.append({
                        'line': i, 'column': 1, 'code': 'COMPOSE005',
                        'message': 'Hardcoded secret - użyj secrets lub .env z ${VAR}'
                    })
        
        # Check for missing restart policy
        if 'restart:' in stripped:
            pass  # Has restart policy
        elif current_service and 'deploy:' not in stripped:
            pass  # Will check at end
        
        # Check for missing healthcheck
        if 'healthcheck:' in stripped:
            pass
        
        # Check for missing resource limits
        if 'mem_limit' in stripped or 'cpus:' in stripped or 'resources:' in stripped:
            pass
    
    # Context-based suggestions
    if len(services) > 1 and not has_networks:
        warnings.append({
            'line': 1, 'column': 1, 'code': 'COMPOSE006',
            'message': f'Zdefiniuj custom networks dla izolacji {len(services)} serwisów'
        })
    
    return {'errors': errors, 'warnings': warnings, 'fixes': fixes,
            'context': {'services': services}}


def analyze_sql(code: str) -> dict:
    """Analyze SQL for common issues and security problems."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    tables_referenced = set()
    tables_created = set()
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        upper_line = stripped.upper()
        
        # Track tables
        if 'CREATE TABLE' in upper_line:
            match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?(\w+)', upper_line)
            if match:
                tables_created.add(match.group(1).lower())
        
        if 'FROM ' in upper_line or 'JOIN ' in upper_line or 'INTO ' in upper_line or 'UPDATE ' in upper_line:
            for match in re.finditer(r'(?:FROM|JOIN|INTO|UPDATE)\s+[`"\[]?(\w+)', upper_line):
                tables_referenced.add(match.group(1).lower())
        
        # Check for SELECT *
        if re.search(r'\bSELECT\s+\*', upper_line):
            warnings.append({
                'line': i, 'column': 1, 'code': 'SQL001',
                'message': 'SELECT * - lepiej wymienić konkretne kolumny'
            })
        
        # Check for SQL injection patterns
        if re.search(r"['\"]?\s*\+\s*\w+\s*\+\s*['\"]?", stripped) or '%s' in stripped or '?' not in stripped:
            if 'WHERE' in upper_line and ('=' in stripped or 'LIKE' in upper_line):
                if "'" in stripped and '+' in stripped:
                    errors.append({
                        'line': i, 'column': 1, 'code': 'SQL002',
                        'message': 'Możliwa podatność SQL injection - użyj prepared statements'
                    })
        
        # Check for missing WHERE in UPDATE/DELETE
        if ('UPDATE ' in upper_line or 'DELETE FROM' in upper_line) and 'WHERE' not in upper_line:
            if ';' in stripped or i == len(lines):
                errors.append({
                    'line': i, 'column': 1, 'code': 'SQL003',
                    'message': 'UPDATE/DELETE bez WHERE - to zmieni wszystkie rekordy!'
                })
        
        # Check for DROP without IF EXISTS
        if 'DROP ' in upper_line and 'IF EXISTS' not in upper_line:
            warnings.append({
                'line': i, 'column': 1, 'code': 'SQL004',
                'message': 'DROP bez IF EXISTS - może wywołać błąd jeśli obiekt nie istnieje'
            })
        
        # Check for CREATE without IF NOT EXISTS
        if 'CREATE TABLE' in upper_line and 'IF NOT EXISTS' not in upper_line:
            warnings.append({
                'line': i, 'column': 1, 'code': 'SQL005',
                'message': 'CREATE TABLE bez IF NOT EXISTS - może wywołać błąd'
            })
        
        # Check for missing indexes hints
        if 'ORDER BY' in upper_line or 'GROUP BY' in upper_line:
            warnings.append({
                'line': i, 'column': 1, 'code': 'SQL006',
                'message': 'ORDER BY/GROUP BY - upewnij się że kolumny mają indeksy'
            })
        
        # Check for GRANT ALL
        if 'GRANT ALL' in upper_line:
            warnings.append({
                'line': i, 'column': 1, 'code': 'SQL007',
                'message': 'GRANT ALL - przyznaj tylko wymagane uprawnienia'
            })
        
        # Check for plain text passwords
        if re.search(r"PASSWORD\s*[=:]\s*['\"][^'\"]+['\"]", upper_line):
            errors.append({
                'line': i, 'column': 1, 'code': 'SQL008',
                'message': 'Hasło w plain text - użyj hashowania'
            })
    
    # Context: check for referenced but not created tables
    missing_tables = tables_referenced - tables_created - {'dual', 'information_schema'}
    
    return {'errors': errors, 'warnings': warnings, 'fixes': fixes,
            'context': {'tables_created': list(tables_created), 'tables_referenced': list(tables_referenced),
                       'potentially_missing': list(missing_tables)}}


def analyze_terraform(code: str) -> dict:
    """Analyze Terraform/HCL for common issues."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    resources = []
    variables_defined = set()
    variables_used = set()
    providers = []
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Track resources
        if stripped.startswith('resource "'):
            match = re.search(r'resource\s+"([^"]+)"\s+"([^"]+)"', stripped)
            if match:
                resources.append({'type': match.group(1), 'name': match.group(2), 'line': i})
        
        # Track variables
        if stripped.startswith('variable "'):
            match = re.search(r'variable\s+"([^"]+)"', stripped)
            if match:
                variables_defined.add(match.group(1))
        
        # Track variable usage
        for match in re.finditer(r'var\.(\w+)', stripped):
            variables_used.add(match.group(1))
        
        # Track providers
        if stripped.startswith('provider "'):
            match = re.search(r'provider\s+"([^"]+)"', stripped)
            if match:
                providers.append(match.group(1))
        
        # Check for hardcoded credentials
        if re.search(r'(access_key|secret_key|password|token)\s*=\s*"[^"$]', stripped, re.IGNORECASE):
            errors.append({
                'line': i, 'column': 1, 'code': 'TF001',
                'message': 'Hardcoded credentials - użyj zmiennych lub vault'
            })
        
        # Check for missing version constraints
        if 'required_providers' in stripped or stripped.startswith('provider "'):
            pass  # Check in context
        
        # Check for public access
        if 'cidr_blocks' in stripped and '0.0.0.0/0' in stripped:
            warnings.append({
                'line': i, 'column': 1, 'code': 'TF002',
                'message': '0.0.0.0/0 otwiera dostęp z całego internetu'
            })
        
        # Check for unencrypted storage
        if 'encrypted' in stripped and 'false' in stripped:
            errors.append({
                'line': i, 'column': 1, 'code': 'TF003',
                'message': 'Wyłączone szyfrowanie - włącz encrypted = true'
            })
        
        # Check for public S3 buckets
        if 'acl' in stripped and ('public-read' in stripped or 'public-read-write' in stripped):
            errors.append({
                'line': i, 'column': 1, 'code': 'TF004',
                'message': 'Publiczny bucket S3 - rozważ prywatne ACL'
            })
        
        # Check for missing tags
        if stripped.startswith('resource "aws_') and 'tags' not in code[code.find(stripped):code.find(stripped)+500]:
            warnings.append({
                'line': i, 'column': 1, 'code': 'TF005',
                'message': 'Brak tags dla zasobu AWS - dodaj tagi dla organizacji'
            })
    
    # Context: undefined variables
    undefined_vars = variables_used - variables_defined
    
    return {'errors': errors, 'warnings': warnings, 'fixes': fixes,
            'context': {'resources': resources, 'providers': providers,
                       'variables_defined': list(variables_defined),
                       'undefined_variables': list(undefined_vars)}}


def analyze_kubernetes(code: str) -> dict:
    """Analyze Kubernetes YAML for common issues."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    kind = None
    has_resources = False
    has_probes = False
    has_security_context = False
    namespace = None
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Track kind
        if stripped.startswith('kind:'):
            kind = stripped.split(':')[1].strip()
        
        # Track namespace
        if stripped.startswith('namespace:'):
            namespace = stripped.split(':')[1].strip()
        
        # Check for resources
        if 'resources:' in stripped:
            has_resources = True
        if 'limits:' in stripped or 'requests:' in stripped:
            has_resources = True
        
        # Check for probes
        if 'livenessProbe:' in stripped or 'readinessProbe:' in stripped:
            has_probes = True
        
        # Check for security context
        if 'securityContext:' in stripped:
            has_security_context = True
        
        # Check for privileged containers
        if 'privileged: true' in stripped:
            errors.append({
                'line': i, 'column': 1, 'code': 'K8S001',
                'message': 'Kontener privileged - poważne ryzyko bezpieczeństwa'
            })
        
        # Check for running as root
        if 'runAsUser: 0' in stripped or 'runAsRoot: true' in stripped:
            warnings.append({
                'line': i, 'column': 1, 'code': 'K8S002',
                'message': 'Kontener uruchamiany jako root'
            })
        
        # Check for hostPath volumes
        if 'hostPath:' in stripped:
            warnings.append({
                'line': i, 'column': 1, 'code': 'K8S003',
                'message': 'hostPath volume - rozważ PersistentVolume'
            })
        
        # Check for latest tag
        if 'image:' in stripped and (':latest' in stripped or ':' not in stripped.split('image:')[1]):
            warnings.append({
                'line': i, 'column': 1, 'code': 'K8S004',
                'message': 'Użyj konkretnego tagu wersji zamiast :latest'
            })
        
        # Check for missing image pull policy
        if 'image:' in stripped and ':latest' in stripped:
            if 'imagePullPolicy' not in code:
                warnings.append({
                    'line': i, 'column': 1, 'code': 'K8S005',
                    'message': 'Brak imagePullPolicy - dla :latest ustaw Always'
                })
        
        # Check for hardcoded secrets
        if stripped.startswith('value:') and any(s in stripped.upper() for s in ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']):
            errors.append({
                'line': i, 'column': 1, 'code': 'K8S006',
                'message': 'Hardcoded secret - użyj Secret resource'
            })
        
        # Check for default namespace
        if stripped == 'namespace: default':
            warnings.append({
                'line': i, 'column': 1, 'code': 'K8S007',
                'message': 'Użycie default namespace - utwórz dedykowany namespace'
            })
    
    # Context-based warnings for Deployments/Pods
    if kind in ('Deployment', 'Pod', 'StatefulSet', 'DaemonSet'):
        if not has_resources:
            warnings.append({
                'line': 1, 'column': 1, 'code': 'K8S008',
                'message': f'Brak resource limits/requests dla {kind}'
            })
        if not has_probes and kind != 'DaemonSet':
            warnings.append({
                'line': 1, 'column': 1, 'code': 'K8S009',
                'message': f'Brak liveness/readiness probes dla {kind}'
            })
        if not has_security_context:
            warnings.append({
                'line': 1, 'column': 1, 'code': 'K8S010',
                'message': f'Brak securityContext dla {kind}'
            })
    
    return {'errors': errors, 'warnings': warnings, 'fixes': fixes,
            'context': {'kind': kind, 'namespace': namespace}}


def analyze_nginx_config(code: str) -> dict:
    """Analyze nginx configuration for common issues."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    has_ssl = False
    has_security_headers = False
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if 'ssl_certificate' in stripped:
            has_ssl = True
        
        if 'add_header' in stripped:
            has_security_headers = True
        
        # Check for server_tokens
        if 'server_tokens on' in stripped:
            warnings.append({
                'line': i, 'column': 1, 'code': 'NGINX001',
                'message': 'server_tokens on ujawnia wersję nginx - ustaw off'
            })
        
        # Check for autoindex
        if 'autoindex on' in stripped:
            warnings.append({
                'line': i, 'column': 1, 'code': 'NGINX002',
                'message': 'autoindex on może ujawnić strukturę katalogów'
            })
        
        # Check for weak SSL protocols
        if 'ssl_protocols' in stripped and ('SSLv3' in stripped or 'TLSv1 ' in stripped or 'TLSv1.0' in stripped):
            errors.append({
                'line': i, 'column': 1, 'code': 'NGINX003',
                'message': 'Słabe protokoły SSL - użyj TLSv1.2 TLSv1.3'
            })
        
        # Check for root inside location
        if stripped.startswith('root ') and 'location' in '\n'.join(lines[max(0,i-5):i]):
            warnings.append({
                'line': i, 'column': 1, 'code': 'NGINX004',
                'message': 'root wewnątrz location może powodować problemy - użyj alias lub root w server'
            })
    
    if has_ssl and not has_security_headers:
        warnings.append({
            'line': 1, 'column': 1, 'code': 'NGINX005',
            'message': 'Brak security headers (HSTS, X-Frame-Options, etc.)'
        })
    
    return {'errors': errors, 'warnings': warnings, 'fixes': fixes}


def analyze_github_actions(code: str) -> dict:
    """Analyze GitHub Actions workflow for common issues."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check for @master/@main instead of version
        if 'uses:' in stripped and ('@master' in stripped or '@main' in stripped):
            warnings.append({
                'line': i, 'column': 1, 'code': 'GHA001',
                'message': 'Użyj konkretnej wersji/SHA zamiast @master/@main'
            })
        
        # Check for pull_request_target
        if 'pull_request_target' in stripped:
            warnings.append({
                'line': i, 'column': 1, 'code': 'GHA002',
                'message': 'pull_request_target może być niebezpieczne - uważaj na injection'
            })
        
        # Check for hardcoded secrets
        if re.search(r'(password|token|key|secret)\s*[:=]\s*["\'][^$\{]', stripped, re.IGNORECASE):
            errors.append({
                'line': i, 'column': 1, 'code': 'GHA003',
                'message': 'Hardcoded secret - użyj ${{ secrets.NAME }}'
            })
        
        # Check for shell injection
        if '${{' in stripped and ('github.event.' in stripped or 'inputs.' in stripped):
            if 'run:' in stripped or (i > 1 and 'run:' in lines[i-2]):
                warnings.append({
                    'line': i, 'column': 1, 'code': 'GHA004',
                    'message': 'Możliwy shell injection - użyj env variable zamiast inline'
                })
        
        # Check for permissions
        if 'permissions:' in stripped:
            pass  # Good
        elif stripped.startswith('jobs:'):
            warnings.append({
                'line': i, 'column': 1, 'code': 'GHA005',
                'message': 'Brak permissions - ustaw minimalne wymagane uprawnienia'
            })
    
    return {'errors': errors, 'warnings': warnings, 'fixes': fixes}


def analyze_ansible(code: str) -> dict:
    """Analyze Ansible playbook for common issues."""
    errors = []
    warnings = []
    fixes = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check for plain text passwords
        if re.search(r'password\s*:\s*["\']?[^\$\{]', stripped, re.IGNORECASE):
            errors.append({
                'line': i, 'column': 1, 'code': 'ANS001',
                'message': 'Plain text password - użyj ansible-vault'
            })
        
        # Check for shell/command without changed_when
        if stripped.startswith('- shell:') or stripped.startswith('- command:'):
            if 'changed_when' not in '\n'.join(lines[i:min(i+5, len(lines))]):
                warnings.append({
                    'line': i, 'column': 1, 'code': 'ANS002',
                    'message': 'shell/command bez changed_when - może dawać fałszywe "changed"'
                })
        
        # Check for become without become_user
        if 'become: true' in stripped or 'become: yes' in stripped:
            if 'become_user' not in '\n'.join(lines[max(0,i-3):i+3]):
                warnings.append({
                    'line': i, 'column': 1, 'code': 'ANS003',
                    'message': 'become bez become_user - domyślnie root'
                })
        
        # Check for ignore_errors
        if 'ignore_errors: true' in stripped or 'ignore_errors: yes' in stripped:
            warnings.append({
                'line': i, 'column': 1, 'code': 'ANS004',
                'message': 'ignore_errors ukrywa błędy - użyj failed_when lub block/rescue'
            })
    
    return {'errors': errors, 'warnings': warnings, 'fixes': fixes}


def detect_language(code: str, filename: str = None) -> str:
    """Detect the programming language of the code."""
    lines = code.strip().split('\n')
    first_line = lines[0] if lines else ''
    
    # Check filename first for config files
    if filename:
        fn_lower = filename.lower()
        if fn_lower == 'dockerfile' or fn_lower.endswith('/dockerfile'):
            return 'dockerfile'
        if fn_lower.endswith(('docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml')):
            return 'docker-compose'
        if fn_lower.endswith('.tf'):
            return 'terraform'
        if fn_lower.endswith('.sql'):
            return 'sql'
        if fn_lower.endswith(('nginx.conf', '.nginx')):
            return 'nginx'
        if fn_lower.endswith(('.yml', '.yaml')) and ('workflow' in fn_lower or '.github' in fn_lower):
            return 'github-actions'
        if fn_lower.endswith(('playbook.yml', 'playbook.yaml', 'ansible.yml')) or 'ansible' in fn_lower:
            return 'ansible'
    
    # Detect by content patterns
    # Dockerfile
    if any(line.strip().upper().startswith(('FROM ', 'RUN ', 'COPY ', 'ENTRYPOINT ', 'CMD ')) for line in lines[:20]):
        if 'FROM ' in code.upper():
            return 'dockerfile'
    
    # Docker Compose
    if 'services:' in code and ('image:' in code or 'build:' in code):
        return 'docker-compose'
    
    # Kubernetes
    if 'apiVersion:' in code and 'kind:' in code:
        return 'kubernetes'
    
    # Terraform
    if 'resource "' in code or 'provider "' in code or 'variable "' in code:
        return 'terraform'
    
    # SQL
    sql_keywords = ['SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ', 'CREATE TABLE', 'DROP ', 'ALTER ']
    if any(kw in code.upper() for kw in sql_keywords):
        return 'sql'
    
    # GitHub Actions
    if 'on:' in code and ('push:' in code or 'pull_request:' in code or 'workflow_dispatch:' in code):
        if 'jobs:' in code or 'steps:' in code:
            return 'github-actions'
    
    # Ansible
    if '- hosts:' in code or '- name:' in code and ('tasks:' in code or 'become:' in code):
        return 'ansible'
    
    # nginx
    if 'server {' in code or 'location ' in code or 'upstream ' in code:
        return 'nginx'
    
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


def analyze_code_multi(code: str, force_language: str = None, filename: str = None) -> dict:
    """Analyze code with automatic language detection."""
    language = force_language or detect_language(code, filename)
    
    result = {
        'originalCode': code,
        'fixedCode': code,
        'errors': [],
        'warnings': [],
        'fixes': [],
        'language': language,
        'context': {}
    }
    
    lang_result = None
    
    # Config file analyzers
    config_analyzers = {
        'dockerfile': analyze_dockerfile,
        'docker-compose': analyze_docker_compose,
        'sql': analyze_sql,
        'terraform': analyze_terraform,
        'kubernetes': analyze_kubernetes,
        'nginx': analyze_nginx_config,
        'github-actions': analyze_github_actions,
        'ansible': analyze_ansible,
    }
    
    # Code analyzers
    code_analyzers = {
        'python': analyze_python_code,
        'php': analyze_php_code,
        'javascript': analyze_javascript_code,
        'nodejs': analyze_javascript_code,
    }
    
    if language in config_analyzers:
        lang_result = config_analyzers[language](code)
        result['errors'] = lang_result.get('errors', [])
        result['warnings'] = lang_result.get('warnings', [])
        result['fixes'] = lang_result.get('fixes', [])
        result['context'] = lang_result.get('context', {})
        result['fixedCode'] = code  # Config files usually don't have auto-fix
        return result
    
    if language in code_analyzers:
        lang_result = code_analyzers[language](code)
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
            
            # Check pactfix API availability
            pactfix_available = False
            if PACTFIX_API_URL:
                try:
                    req = urllib.request.Request(f"{PACTFIX_API_URL}/api/health")
                    with urllib.request.urlopen(req, timeout=2) as resp:
                        pactfix_available = resp.status == 200
                except:
                    pass
            
            health = {
                'status': 'healthy',
                'version': '1.2.0',
                'features': {
                    'shellcheck': shellcheck_available,
                    'bash_analysis': True,
                    'python_analysis': True,
                    'auto_fix': True,
                    'pactfix_api': pactfix_available,
                    'pactfix_url': PACTFIX_API_URL or None
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
                filename = data.get('filename')
                
                logger.info(f"Analyzing code ({len(code)} chars)")
                
                # Try pactfix API service first if configured
                result = None
                if PACTFIX_API_URL:
                    result = self._call_pactfix_api(data)
                
                # Fallback to local analysis
                if result is None:
                    result = analyze_code_multi(code, filename=filename)
                
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
    
    def _call_pactfix_api(self, data: dict) -> dict:
        """Call the pactfix API service."""
        try:
            req = urllib.request.Request(
                f"{PACTFIX_API_URL}/api/analyze",
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                logger.info(f"Pactfix API response: {result.get('language', 'unknown')}")
                return result
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            logger.warning(f"Pactfix API error, falling back to local: {e}")
            return None
        except Exception as e:
            logger.warning(f"Pactfix API exception: {e}")
            return None
    
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
