"""Multi-language code and config file analyzer."""

import ast
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path

SUPPORTED_LANGUAGES = [
    'bash', 'python', 'php', 'javascript', 'nodejs',
    'dockerfile', 'docker-compose', 'sql', 'terraform',
    'kubernetes', 'nginx', 'github-actions', 'ansible',
    'typescript', 'go', 'rust', 'java', 'csharp', 'ruby',
    'makefile', 'yaml', 'apache', 'systemd', 'html', 'css',
    'json', 'toml', 'ini',
    'helm']

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
    description: str
    before: str
    after: str
    edits: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AnalysisResult:
    language: str
    original_code: str
    fixed_code: str
    errors: List[Issue] = field(default_factory=list)
    warnings: List[Issue] = field(default_factory=list)
    fixes: List[Fix] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'language': self.language,
            'originalCode': self.original_code,
            'fixedCode': self.fixed_code,
            'errors': [asdict(e) for e in self.errors],
            'warnings': [asdict(w) for w in self.warnings],
            'fixes': [{**asdict(f), 'message': f.description} for f in self.fixes],
            'context': self.context
        }


def detect_language(code: str, filename: str = None) -> str:
    """Detect the language/format of the code."""
    lines = code.strip().split('\n')
    first_line = lines[0] if lines else ''
    
    if filename:
        fn_lower = filename.lower()
        fn_name = Path(filename).name.lower()
        
        if fn_name == 'dockerfile' or fn_lower.endswith('/dockerfile'):
            return 'dockerfile'
        if any(fn_lower.endswith(x) for x in ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']):
            return 'docker-compose'
        if fn_lower.endswith('.tf'):
            return 'terraform'
        if fn_lower.endswith('.sql'):
            return 'sql'
        if fn_lower.endswith('nginx.conf') or '.nginx' in fn_lower:
            return 'nginx'
        if fn_lower.endswith(('.yml', '.yaml')) and ('workflow' in fn_lower or '.github' in fn_lower):
            return 'github-actions'
        if any(x in fn_lower for x in ['playbook', 'ansible']):
            return 'ansible'
        if fn_name in ('chart.yaml', 'chart.yml', 'values.yaml', 'values.yml'):
            return 'helm'
        if '/templates/' in fn_lower and fn_lower.endswith(('.yml', '.yaml')):
            return 'helm'
        if fn_lower.endswith(('.tpl', '.gotmpl')):
            return 'helm'
        if fn_lower.endswith(('.yml', '.yaml')):
            return 'yaml'
        if fn_lower.endswith('.py'):
            return 'python'
        if fn_lower.endswith('.php'):
            return 'php'
        if fn_lower.endswith('.js'):
            if 'require(' in code or 'module.exports' in code:
                return 'nodejs'
            return 'javascript'
        if fn_lower.endswith('.sh'):
            return 'bash'
        if fn_lower.endswith('.ts') or fn_lower.endswith('.tsx'):
            return 'typescript'
        if fn_lower.endswith('.go'):
            return 'go'
        if fn_lower.endswith('.rs'):
            return 'rust'
        if fn_lower.endswith('.java'):
            return 'java'
        if fn_lower.endswith('.cs'):
            return 'csharp'
        if fn_lower.endswith('.rb'):
            return 'ruby'
        if fn_lower.endswith('.json') or fn_lower.endswith('.jsonc'):
            return 'json'
        if fn_lower.endswith('.toml'):
            return 'toml'
        if fn_lower.endswith('.ini') or fn_lower.endswith('.cfg'):
            return 'ini'
        if fn_name == 'makefile' or fn_lower.endswith('.mk'):
            return 'makefile'
        if fn_lower.endswith('.html') or fn_lower.endswith('.htm'):
            return 'html'
        if fn_lower.endswith('.css'):
            return 'css'
        if fn_lower.endswith('.conf') and 'apache' in fn_lower:
            return 'apache'
        if fn_lower.endswith('.service') or fn_lower.endswith('.timer'):
            return 'systemd'

    # Content-based detection
    if any(line.strip().upper().startswith(('FROM ', 'RUN ', 'COPY ', 'ENTRYPOINT ')) for line in lines[:20]):
        if 'FROM ' in code.upper():
            return 'dockerfile'
    
    if 'services:' in code and ('image:' in code or 'build:' in code):
        return 'docker-compose'
    
    if 'apiVersion:' in code and 'kind:' in code:
        return 'kubernetes'
    
    if 'resource "' in code or 'provider "' in code or 'variable "' in code:
        return 'terraform'
    
    sql_keywords = ['SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ', 'CREATE TABLE', 'DROP ']
    if any(kw in code.upper() for kw in sql_keywords):
        return 'sql'
    
    if 'on:' in code and ('push:' in code or 'pull_request:' in code) and 'jobs:' in code:
        return 'github-actions'
    
    if '- hosts:' in code or ('- name:' in code and 'tasks:' in code):
        return 'ansible'

    if '{{' in code and '}}' in code and ('.Values' in code or '.Release' in code or '.Chart' in code):
        return 'helm'
    
    if 'server {' in code or 'location ' in code:
        return 'nginx'
    
    # TypeScript detection
    if 'interface ' in code and '{' in code and (':' in code or 'export ' in code):
        return 'typescript'
    
    # Go detection
    if 'package ' in code and ('func ' in code or 'import (' in code):
        return 'go'
    
    # Rust detection
    if 'fn ' in code and ('let ' in code or 'use ' in code) and '::' in code:
        return 'rust'
    
    # Java detection
    if ('public class ' in code or 'private class ' in code) and 'void ' in code:
        return 'java'
    
    # C# detection
    if 'namespace ' in code and ('class ' in code or 'interface ' in code):
        return 'csharp'
    
    # Ruby detection
    if 'def ' in code and 'end' in code and ('class ' in code or 'module ' in code):
        return 'ruby'
    
    yaml_key_lines = sum(1 for l in lines if re.match(r'^\s*[A-Za-z0-9_.-]+\s*:\s*\S?', l))
    has_makefile_recipe = re.search(r'^\t(?!\s*[A-Za-z0-9_.-]+\s*:)\S', code, re.MULTILINE) is not None
    if yaml_key_lines >= 3 and not has_makefile_recipe and not re.search(r'^\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*\s*[:+?]?=\s*', code, re.MULTILINE):
        return 'yaml'
    
    # Makefile detection
    if (re.search(r'^[A-Za-z0-9_.-]+:\s*$', code, re.MULTILINE) or '.PHONY:' in code) and (has_makefile_recipe or '.PHONY:' in code):
        return 'makefile'
    
    # HTML detection
    if '<!DOCTYPE' in code.upper() or '<html' in code.lower():
        return 'html'
    
    # CSS detection
    if re.search(r'[.#]\w+\s*\{', code) and ':' in code and ';' in code:
        return 'css'
    
    # Apache config detection
    if '<VirtualHost' in code or 'ServerName' in code or 'DocumentRoot' in code:
        return 'apache'
    
    # Systemd unit detection
    if '[Unit]' in code or '[Service]' in code or '[Install]' in code:
        return 'systemd'
    
    if first_line.startswith('#!'):
        if 'python' in first_line.lower():
            return 'python'
        if 'bash' in first_line or 'sh' in first_line:
            return 'bash'
        if 'node' in first_line:
            return 'nodejs'
    
    if '<?php' in code:
        return 'php'
    
    python_patterns = [r'^def\s+\w+\s*\(', r'^class\s+\w+.*:', r'^import\s+\w+', r'^from\s+\w+\s+import']
    for pattern in python_patterns:
        if any(re.search(pattern, line) for line in lines):
            return 'python'
    
    if 'require(' in code or 'module.exports' in code:
        return 'nodejs'
    
    js_patterns = [r'\bconst\s+\w+\s*=', r'\blet\s+\w+\s*=', r'\bvar\s+\w+\s*=', r'function\s+\w+\s*\(']
    for pattern in js_patterns:
        if any(re.search(pattern, line) for line in lines):
            return 'javascript'
    
    # INI/TOML/JSON detection
    # JSON: starts with { or [ and contains :
    stripped_code = code.lstrip()
    if stripped_code.startswith('{') or stripped_code.startswith('['):
        if ':' in code:
            return 'json'
    # TOML: section headers [x] or key = value
    if re.search(r'^\s*\[[^\]]+\]\s*$', code, re.MULTILINE) and '=' in code:
        return 'toml'
    # INI: section headers [x] and key=value
    if re.search(r'^\s*\[[^\]]+\]\s*$', code, re.MULTILINE) and re.search(r'^\s*[^#;\[][^=]*=', code, re.MULTILINE):
        return 'ini'

    return 'bash'


def add_fix_comments(result: AnalysisResult) -> str:
    if result.language == 'json':
        return result.fixed_code

    if not result.fixes:
        return result.fixed_code

    comment_prefix_by_language = {
        'python': '#',
        'bash': '#',
        'php': '//',
        'javascript': '//',
        'nodejs': '//',
        'dockerfile': '#',
        'docker-compose': '#',
        'sql': '--',
        'terraform': '#',
        'kubernetes': '#',
        'nginx': '#',
        'github-actions': '#',
        'ansible': '#',
        'typescript': '//',
        'go': '//',
        'rust': '//',
        'java': '//',
        'csharp': '//',
        'ruby': '#',
        'makefile': '#',
        'yaml': '#',
        'helm': '#',
        'toml': '#',
        'ini': ';',
        'apache': '#',
        'systemd': '#',
        'html': '<!--',
        'css': '/*',
    }
    comment_suffix_by_language = {
        'html': ' -->',
        'css': ' */',
    }
    prefix = comment_prefix_by_language.get(result.language, '#')
    suffix = comment_suffix_by_language.get(result.language, '')

    lines = result.fixed_code.split('\n')
    fixes_by_line: Dict[int, List[Fix]] = {}
    for fx in result.fixes:
        fixes_by_line.setdefault(fx.line, []).append(fx)

    for line_no in sorted(fixes_by_line.keys(), reverse=True):
        idx = line_no - 1
        if idx < 0 or idx >= len(lines):
            continue

        indent_match = re.match(r'^\s*', lines[idx])
        indent = indent_match.group(0) if indent_match else ''

        parts = []
        for fx in fixes_by_line[line_no]:
            before = (fx.before or '').strip().replace('\n', ' ')
            if len(before) > 80:
                before = before[:77] + '...'
            parts.append(f"{fx.description} (was: {before})")

        msg = '; '.join(parts)
        if len(msg) > 220:
            msg = msg[:217] + '...'

        comment_line = f"{indent}{prefix} pactfix: {msg}{suffix}"
        lines.insert(idx, comment_line)

    return '\n'.join(lines)


def _apply_edits_to_lines(lines: List[str], edits: List[Dict[str, Any]]) -> List[str]:
    if not edits:
        return lines

    sorted_edits = sorted(
        edits,
        key=lambda e: (-(int(e.get('startLine') or 0)), -(int(e.get('endLine') or 0))),
    )

    out = list(lines)
    for e in sorted_edits:
        try:
            start_line = int(e.get('startLine'))
            end_line = int(e.get('endLine'))
        except Exception:
            continue

        replacement = '' if e.get('replacement') is None else str(e.get('replacement'))
        replacement_lines = [] if replacement == '' else replacement.split('\n')

        start_idx = start_line - 1
        if start_idx < 0 or start_idx > len(out):
            continue

        if end_line < start_line:
            out[start_idx:start_idx] = replacement_lines
            continue

        end_idx = end_line - 1
        delete_count = max(0, min(len(out) - start_idx, end_idx - start_idx + 1))

        if e.get('preserveIndent') and delete_count == 1 and len(replacement_lines) == 1:
            indent_match = re.match(r'^\s*', out[start_idx] if start_idx < len(out) else '')
            indent = indent_match.group(0) if indent_match else ''
            without_indent = re.sub(r'^\s*', '', replacement_lines[0])
            replacement_lines = [indent + without_indent]

        out[start_idx:start_idx + delete_count] = replacement_lines

    return out


def _brace_unbraced_bash_vars(line: str) -> str:
    out = []
    i = 0
    in_single = False
    in_double = False
    escaped = False
    while i < len(line):
        ch = line[i]
        if escaped:
            out.append(ch)
            escaped = False
            i += 1
            continue
        if ch == '\\':
            out.append(ch)
            escaped = True
            i += 1
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            out.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
            i += 1
            continue
        if ch == '$' and not in_single:
            if i + 1 < len(line) and line[i + 1] == '{':
                out.append(ch)
                i += 1
                continue
            if i + 1 < len(line) and re.match(r'[A-Za-z_]', line[i + 1]):
                j = i + 2
                while j < len(line) and re.match(r'[A-Za-z0-9_]', line[j]):
                    j += 1
                name = line[i + 1:j]
                out.append('${' + name + '}')
                i = j
                continue
        out.append(ch)
        i += 1
    return ''.join(out)


def _split_bash_comment(line: str) -> tuple[str, str]:
    in_single = False
    in_double = False
    escaped = False
    for i, ch in enumerate(line):
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            continue
        if ch == '#' and not in_single and not in_double:
            return line[:i], line[i:]
    return line, ''


def _split_python_comment(line: str) -> tuple[str, str]:
    in_single = False
    in_double = False
    escaped = False
    for i, ch in enumerate(line):
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            continue
        if ch == '#' and not in_single and not in_double:
            return line[:i], line[i:]
    return line, ''


def analyze_bash(code: str) -> AnalysisResult:
    """Analyze Bash script."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    fixed_lines = lines.copy()
    
    for i, line in enumerate(lines, 1):
        current_line = fixed_lines[i-1]
        stripped = current_line.strip()
        
        # Variables without braces: use ${VAR} for clarity (e.g. ${OUTPUT}/${HOST})
        if not stripped.startswith('#') and '$' in current_line and re.search(r'\$[A-Za-z_][A-Za-z0-9_]*', current_line):
            code_part, comment_part = _split_bash_comment(current_line)
            braced_code_part = _brace_unbraced_bash_vars(code_part)
            if braced_code_part != code_part:
                new_line = braced_code_part + comment_part
                warnings.append(Issue(i, 1, 'BASH001', 'Zmienne bez klamerek: użyj składni ${VAR} (np. ${OUTPUT}/${HOST})'))
                fixes.append(Fix(i, 'Dodano klamerki do zmiennych', current_line.strip(), new_line.strip()))
                current_line = new_line
                stripped = current_line.strip()
        
        # SC2164: cd without error handling
        if re.match(r'^cd\s+', stripped) and '||' not in stripped and '&&' not in stripped:
            warnings.append(Issue(i, 1, 'SC2164', 'cd bez obsługi błędów - użyj cd ... || exit'))
            fix_line = stripped + ' || exit 1'
            fixes.append(Fix(i, 'Dodano obsługę błędów dla cd', stripped, fix_line))
            current_line = current_line.replace(stripped, fix_line)
            stripped = fix_line
        
        # SC2162: read without -r
        if re.match(r'^read\s+', stripped) and '-r' not in stripped:
            warnings.append(Issue(i, 1, 'SC2162', 'read bez -r może interpretować backslashe'))
        
        # Check for misplaced quotes
        quote_match = re.search(r'(\w+)="([^"]*)"(\w+)', stripped)
        if quote_match:
            errors.append(Issue(i, 1, 'SC1073', 'Błędne umiejscowienie cudzysłowów'))
            fixed = f'{quote_match.group(1)}="{quote_match.group(2)}{quote_match.group(3)}"'
            fixes.append(Fix(i, 'Poprawiono cudzysłowy', quote_match.group(0), fixed))
            current_line = current_line.replace(quote_match.group(0), fixed)
        
        fixed_lines[i-1] = current_line
    
    return AnalysisResult('bash', code, '\n'.join(fixed_lines), errors, warnings, fixes)


def analyze_python(code: str) -> AnalysisResult:
    """Analyze Python code."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    fixed_lines = lines.copy()
    
    for i, line in enumerate(lines, 1):
        current_line = fixed_lines[i - 1]
        stripped = current_line.strip()
        code_part, comment_part = _split_python_comment(current_line)
        code_stripped = code_part.strip()
        in_condition_stmt = code_stripped.startswith(('if ', 'elif ', 'while ', 'assert '))

        if re.match(r'^\s*def\s+\w+\s*\(', current_line):
            next_non_empty = ''
            next_idx = i
            while next_idx < len(fixed_lines):
                probe = fixed_lines[next_idx]
                if probe.strip() != '':
                    next_non_empty = probe.strip()
                    break
                next_idx += 1
            if next_non_empty and not next_non_empty.startswith(('"""', "'''")):
                warnings.append(Issue(i, 1, 'PY006', 'Funkcja nie ma docstringa'))
                def_indent_match = re.match(r'^\s*', current_line)
                def_indent = def_indent_match.group(0) if def_indent_match else ''
                body_indent = def_indent + '    '
                if next_idx < len(fixed_lines):
                    probe_indent_match = re.match(r'^\s*', fixed_lines[next_idx])
                    probe_indent = probe_indent_match.group(0) if probe_indent_match else ''
                    if len(probe_indent) > len(def_indent):
                        body_indent = probe_indent
                doc_line = f'{body_indent}"""TODO: docstring."""'
                edit = {'startLine': i + 1, 'endLine': i, 'replacement': doc_line}
                fixes.append(Fix(i, 'Dodano szablon docstringa', current_line.strip(), '', edits=[edit]))
        
        # Python 2 print statement
        if re.match(r'^print\s+["\']', stripped) or re.match(r'^print\s+\w', stripped):
            if not stripped.startswith('print('):
                errors.append(Issue(i, 1, 'PY001', 'Użyj print() z nawiasami (Python 3)'))
                match = re.match(r'^print\s+(.+)$', stripped)
                if match:
                    fixed = f'print({match.group(1)})'
                    fixes.append(Fix(i, 'Dodano nawiasy do print()', stripped, fixed))
                    fixed_lines[i - 1] = current_line.replace(stripped, fixed)
                    current_line = fixed_lines[i - 1]
                    code_part, comment_part = _split_python_comment(current_line)
                    code_stripped = code_part.strip()
                    stripped = current_line.strip()
        
        # Bare except
        if re.match(r'^except\s*:', code_stripped):
            warnings.append(Issue(i, 1, 'PY002', 'Unikaj pustego except: - złap konkretne wyjątki'))
            if re.match(r'^except\s*:\s*$', code_stripped):
                fixed = re.sub(r'^except\s*:\s*$', 'except Exception:', code_stripped)
                if fixed != code_stripped:
                    fixes.append(Fix(i, 'Zmieniono except: na except Exception:', code_stripped, fixed))
                    fixed_lines[i - 1] = (code_part[:len(code_part) - len(code_part.lstrip())] + fixed + comment_part)
                    current_line = fixed_lines[i - 1]
                    code_part, comment_part = _split_python_comment(current_line)
                    code_stripped = code_part.strip()
                    stripped = current_line.strip()
        
        # Mutable default argument
        if re.search(r'def\s+\w+\s*\([^)]*=\s*(\[\]|\{\})', stripped):
            warnings.append(Issue(i, 1, 'PY003', 'Mutable default argument - użyj None'))
            m = re.match(r'^(\s*def\s+\w+\s*\()(?P<args>[^)]*)(\)\s*:.*)$', current_line)
            if m:
                args = m.group('args')
                arg_match = re.search(r'(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<lit>\[\]|\{\})', args)
                if arg_match:
                    name = arg_match.group('name')
                    lit = arg_match.group('lit')
                    new_args = args.replace(arg_match.group(0), f"{name}=None")
                    new_def_line = current_line.replace(args, new_args)

                    next_line = fixed_lines[i] if i < len(fixed_lines) else ''
                    if re.search(rf'^\s*if\s+{re.escape(name)}\s+is\s+None\s*:', next_line or ''):
                        pass
                    else:
                        def_indent_match = re.match(r'^\s*', current_line)
                        def_indent = def_indent_match.group(0) if def_indent_match else ''
                        body_indent = def_indent + '    '
                        for j in range(i, len(fixed_lines)):
                            probe = fixed_lines[j]
                            if probe.strip() == '':
                                continue
                            probe_indent_match = re.match(r'^\s*', probe)
                            probe_indent = probe_indent_match.group(0) if probe_indent_match else ''
                            if len(probe_indent) > len(def_indent):
                                body_indent = probe_indent
                            break

                        init_line = f"{body_indent}if {name} is None: {name} = {lit}"
                        fixes.append(
                            Fix(
                                i,
                                f'Zmieniono mutable default argument {name} na None',
                                current_line.strip(),
                                new_def_line.strip(),
                                edits=[
                                    {
                                        'startLine': i,
                                        'endLine': i,
                                        'replacement': new_def_line,
                                        'preserveIndent': True,
                                    },
                                    {
                                        'startLine': i + 1,
                                        'endLine': i,
                                        'replacement': init_line,
                                    },
                                ],
                            )
                        )
        
        # == None instead of is None
        if in_condition_stmt and ('== None' in code_part or '!= None' in code_part):
            warnings.append(Issue(i, 1, 'PY004', 'Użyj "is None" zamiast "== None"'))
            fixed_code = code_part
            fixed_code = re.sub(r'==\s*None\b', 'is None', fixed_code)
            fixed_code = re.sub(r'!=\s*None\b', 'is not None', fixed_code)
            if fixed_code != code_part:
                before = code_part.strip()
                after = fixed_code.strip()
                fixes.append(Fix(i, 'Zmieniono porównanie do None na is None/is not None', before, after))
                fixed_lines[i - 1] = fixed_code + comment_part
                current_line = fixed_lines[i - 1]
                code_part, comment_part = _split_python_comment(current_line)
                code_stripped = code_part.strip()
                stripped = current_line.strip()

        # type(x) == T instead of isinstance(x, T)
        m_type_cmp = None
        if in_condition_stmt:
            m_type_cmp = re.search(
                r'\btype\s*\(\s*(?P<expr>[^)]+?)\s*\)\s*==\s*(?P<typ>list|dict|tuple|set)\b',
                code_part,
            )
        if m_type_cmp:
            warnings.append(Issue(i, 1, 'PY007', 'Rozważ isinstance() zamiast type() == ...'))
            expr = m_type_cmp.group('expr')
            typ = m_type_cmp.group('typ')
            before = m_type_cmp.group(0)
            after = f'isinstance({expr}, {typ})'
            fixed_code = code_part.replace(before, after)
            if fixed_code != code_part:
                fixes.append(Fix(i, 'Zamieniono type(x) == T na isinstance(x, T)', before.strip(), after.strip()))
                fixed_lines[i - 1] = fixed_code + comment_part
                current_line = fixed_lines[i - 1]
                code_part, comment_part = _split_python_comment(current_line)
                code_stripped = code_part.strip()
                stripped = current_line.strip()

        # Using 'is'/'is not' for literal string/int comparison
        literal_pat = r'("[^"]*"|\'[^\']*\'|\d+)'
        tail_pat = r'(?=\s|$|:|,|\)|\]|\})'
        is_not_pat = rf'\bis\s+not\s+(?!None\b){literal_pat}{tail_pat}'
        is_pat = rf'\bis\s+(?!None\b){literal_pat}{tail_pat}'
        if in_condition_stmt and (re.search(is_not_pat, code_part) or re.search(is_pat, code_part)):
            warnings.append(Issue(i, 1, 'PY008', 'Nie używaj "is" do porównań z literałami - użyj =='))
            fixed_code = code_part
            fixed_code = re.sub(is_not_pat, r'!= \1', fixed_code)
            fixed_code = re.sub(is_pat, r'== \1', fixed_code)
            if fixed_code != code_part:
                fixes.append(Fix(i, 'Zamieniono "is" na == dla literałów', code_part.strip(), fixed_code.strip()))
                fixed_lines[i - 1] = fixed_code + comment_part
                current_line = fixed_lines[i - 1]
                code_part, comment_part = _split_python_comment(current_line)
                code_stripped = code_part.strip()
                stripped = current_line.strip()

    try:
        tree = ast.parse('\n'.join(fixed_lines))
        used_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and getattr(node, 'lineno', None):
                if len(node.names) != 1:
                    continue
                alias = node.names[0]
                imported = alias.asname or alias.name.split('.')[0]
                if imported in used_names:
                    continue
                line_no = int(node.lineno)
                before_line = fixed_lines[line_no - 1] if 0 < line_no <= len(fixed_lines) else ''
                warnings.append(Issue(line_no, 1, 'PY005', f'Import "{imported}" może być nieużywany'))
                edit = {'startLine': line_no, 'endLine': line_no, 'replacement': ''}
                fixes.append(Fix(line_no, f'Usunięto nieużywany import: {imported}', before_line.strip(), '', edits=[edit]))

            if isinstance(node, ast.ImportFrom) and getattr(node, 'lineno', None):
                if len(node.names) != 1:
                    continue
                alias = node.names[0]
                imported = alias.asname or alias.name
                if imported in used_names:
                    continue
                line_no = int(node.lineno)
                before_line = fixed_lines[line_no - 1] if 0 < line_no <= len(fixed_lines) else ''
                warnings.append(Issue(line_no, 1, 'PY005', f'Import "{imported}" może być nieużywany'))
                edit = {'startLine': line_no, 'endLine': line_no, 'replacement': ''}
                fixes.append(Fix(line_no, f'Usunięto nieużywany import: {imported}', before_line.strip(), '', edits=[edit]))
    except Exception:
        pass

    return AnalysisResult('python', code, '\n'.join(fixed_lines), errors, warnings, fixes)


def analyze_php(code: str) -> AnalysisResult:
    """Analyze PHP code."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if re.search(r'\$_(GET|POST|REQUEST|COOKIE)\[', stripped):
            if 'htmlspecialchars' not in stripped and 'filter_' not in stripped:
                warnings.append(Issue(i, 1, 'PHP001', 'Niezwalidowane dane wejściowe - użyj filter_input lub htmlspecialchars'))
        
        if '==' in stripped and ('null' in stripped.lower() or 'false' in stripped.lower()):
            warnings.append(Issue(i, 1, 'PHP002', 'Użyj === zamiast == dla porównań'))
        
        if re.search(r'\bmysql_(connect|query|fetch)', stripped):
            errors.append(Issue(i, 1, 'PHP003', 'Przestarzałe funkcje mysql_* - użyj PDO lub mysqli'))
        
        if 'extract(' in stripped:
            errors.append(Issue(i, 1, 'PHP004', 'extract() jest niebezpieczne - użyj jawnego przypisania'))
        
        if stripped.startswith('@'):
            warnings.append(Issue(i, 1, 'PHP005', 'Operator @ tłumi błędy - obsłuż je prawidłowo'))
        
        if '<?=' in stripped or re.match(r'^<\?\s+', stripped):
            warnings.append(Issue(i, 1, 'PHP006', 'Użyj pełnego <?php zamiast short tags'))
    
    return AnalysisResult('php', code, code, errors, warnings, fixes)


def analyze_javascript(code: str, is_nodejs: bool = False) -> AnalysisResult:
    """Analyze JavaScript/Node.js code."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    fixed_lines = lines.copy()
    lang = 'nodejs' if is_nodejs else 'javascript'
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # var usage
        if re.search(r'\bvar\s+\w+', stripped):
            warnings.append(Issue(i, 1, 'JS001', 'Użyj let/const zamiast var'))
            fixed = re.sub(r'\bvar\b', 'let', stripped)
            fixes.append(Fix(i, 'Zamieniono var na let', stripped, fixed))
            fixed_lines[i-1] = line.replace(stripped, fixed)
        
        # == instead of ===
        if re.search(r'[^=!]={2}[^=]', stripped) and '===' not in stripped:
            warnings.append(Issue(i, 1, 'JS002', 'Użyj === zamiast =='))
        
        # console.log in production
        if 'console.log' in stripped:
            warnings.append(Issue(i, 1, 'JS003', 'console.log w kodzie produkcyjnym'))
        
        # eval usage
        if 'eval(' in stripped:
            errors.append(Issue(i, 1, 'JS004', 'eval() jest niebezpieczne - unikaj'))
        
        # Node.js specific
        if is_nodejs:
            if re.search(r'\b(readFileSync|writeFileSync)\b', stripped):
                warnings.append(Issue(i, 1, 'NODE002', 'Sync I/O blokuje event loop - użyj async'))
    
    return AnalysisResult(lang, code, '\n'.join(fixed_lines), errors, warnings, fixes)


def analyze_dockerfile(code: str) -> AnalysisResult:
    """Analyze Dockerfile."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    fixed_lines = lines.copy()
    
    has_user = False
    has_healthcheck = False
    base_image = None
    env_vars = set()
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        upper = stripped.upper()
        
        if upper.startswith('FROM '):
            base_image = stripped[5:].strip().split()[0]
            if ':latest' in base_image or (':' not in base_image and '@' not in base_image):
                warnings.append(Issue(i, 1, 'DOCKER001', f'Użyj konkretnego tagu zamiast :latest dla {base_image}'))
                if ':' not in base_image:
                    fixed = stripped + ':latest  # TODO: specify version'
                    fixes.append(Fix(i, 'Dodano placeholder dla wersji', stripped, fixed))
        
        if upper.startswith('USER '):
            has_user = True
        
        if upper.startswith('HEALTHCHECK '):
            has_healthcheck = True
        
        if upper.startswith('ENV '):
            parts = stripped[4:].split('=')
            if parts:
                env_vars.add(parts[0].strip())
        
        if upper.startswith('RUN ') and 'apt-get install' in stripped:
            if 'rm -rf /var/lib/apt/lists' not in stripped and '&&' not in stripped:
                warnings.append(Issue(i, 1, 'DOCKER002', 'apt-get install bez czyszczenia cache'))
            if 'apt-get update' not in stripped:
                warnings.append(Issue(i, 1, 'DOCKER003', 'apt-get install bez update w tej samej warstwie'))
        
        if upper.startswith('ADD ') and 'http' not in stripped and '.tar' not in stripped:
            warnings.append(Issue(i, 1, 'DOCKER004', 'Użyj COPY zamiast ADD dla lokalnych plików'))
            fixed = 'COPY' + stripped[3:]
            fixes.append(Fix(i, 'Zamieniono ADD na COPY', stripped, fixed))
            fixed_lines[i-1] = line.replace(stripped, fixed)
        
        if upper.startswith('WORKDIR ') and not stripped[8:].strip().startswith('/'):
            warnings.append(Issue(i, 1, 'DOCKER008', 'WORKDIR powinien używać ścieżki absolutnej'))
            fixed = 'WORKDIR /' + stripped[8:].strip()
            fixes.append(Fix(i, 'Dodano / do WORKDIR', stripped, fixed))
            fixed_lines[i-1] = line.replace(stripped, fixed)
        
        secret_patterns = ['PASSWORD=', 'SECRET=', 'API_KEY=', 'TOKEN=']
        for pattern in secret_patterns:
            if pattern in upper and 'ARG' not in upper:
                errors.append(Issue(i, 1, 'DOCKER007', 'Hardcoded secret - użyj build args lub secrets'))
        
        if (upper.startswith('CMD ') or upper.startswith('ENTRYPOINT ')) and '[' not in stripped:
            warnings.append(Issue(i, 1, 'DOCKER006', 'Użyj formy exec (JSON array) dla CMD/ENTRYPOINT'))
    
    if not has_user:
        warnings.append(Issue(1, 1, 'DOCKER009', 'Brak USER - kontener będzie działał jako root'))
    
    if not has_healthcheck and base_image:
        warnings.append(Issue(1, 1, 'DOCKER010', 'Brak HEALTHCHECK'))
    
    context = {'base_image': base_image, 'env_vars': list(env_vars)}
    return AnalysisResult('dockerfile', code, '\n'.join(fixed_lines), errors, warnings, fixes, context)


def analyze_docker_compose(code: str) -> AnalysisResult:
    """Analyze docker-compose.yml."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    
    services = []
    has_networks = False
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        
        if indent == 2 and stripped.endswith(':') and not stripped.startswith('-'):
            services.append(stripped[:-1])
        
        if 'networks:' in stripped and indent == 0:
            has_networks = True
        
        if 'image:' in stripped and (':latest' in stripped or ':' not in stripped.split('image:')[1].strip()):
            warnings.append(Issue(i, 1, 'COMPOSE001', 'Użyj konkretnego tagu wersji'))
        
        if 'privileged: true' in stripped:
            errors.append(Issue(i, 1, 'COMPOSE002', 'privileged: true jest niebezpieczne'))
        
        if 'network_mode: host' in stripped:
            warnings.append(Issue(i, 1, 'COMPOSE003', 'network_mode: host omija izolację'))
        
        if '/var/run/docker.sock' in stripped:
            errors.append(Issue(i, 1, 'COMPOSE004', 'Montowanie docker.sock daje pełny dostęp'))
        
        secret_patterns = ['PASSWORD=', 'SECRET=', 'API_KEY=', 'TOKEN=']
        for pattern in secret_patterns:
            if pattern in stripped.upper() and '${' not in stripped:
                errors.append(Issue(i, 1, 'COMPOSE005', 'Hardcoded secret - użyj .env'))
    
    if len(services) > 1 and not has_networks:
        warnings.append(Issue(1, 1, 'COMPOSE006', f'Zdefiniuj networks dla {len(services)} serwisów'))
    
    return AnalysisResult('docker-compose', code, code, errors, warnings, fixes, {'services': services})


def analyze_sql(code: str) -> AnalysisResult:
    """Analyze SQL."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    fixed_lines = lines.copy()
    
    tables_created = set()
    tables_referenced = set()
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        upper = stripped.upper()
        
        if 'CREATE TABLE' in upper:
            match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?(\w+)', upper)
            if match:
                tables_created.add(match.group(1).lower())
        
        if any(kw in upper for kw in ['FROM ', 'JOIN ', 'INTO ', 'UPDATE ']):
            for match in re.finditer(r'(?:FROM|JOIN|INTO|UPDATE)\s+[`"\[]?(\w+)', upper):
                tables_referenced.add(match.group(1).lower())
        
        if re.search(r'\bSELECT\s+\*', upper):
            warnings.append(Issue(i, 1, 'SQL001', 'SELECT * - wymień konkretne kolumny'))
        
        if ('UPDATE ' in upper or 'DELETE FROM' in upper) and 'WHERE' not in upper:
            if ';' in stripped or i == len(lines):
                errors.append(Issue(i, 1, 'SQL003', 'UPDATE/DELETE bez WHERE!'))
        
        if 'DROP ' in upper and 'IF EXISTS' not in upper:
            warnings.append(Issue(i, 1, 'SQL004', 'DROP bez IF EXISTS'))
            fixed = stripped.replace('DROP ', 'DROP IF EXISTS ', 1)
            fixes.append(Fix(i, 'Dodano IF EXISTS', stripped, fixed))
            fixed_lines[i-1] = line.replace(stripped, fixed)
        
        if 'CREATE TABLE' in upper and 'IF NOT EXISTS' not in upper:
            warnings.append(Issue(i, 1, 'SQL005', 'CREATE bez IF NOT EXISTS'))
        
        if 'GRANT ALL' in upper:
            warnings.append(Issue(i, 1, 'SQL007', 'GRANT ALL - przyznaj tylko wymagane uprawnienia'))
        
        if re.search(r"PASSWORD\s*[=:]\s*['\"][^'\"]+['\"]", upper):
            errors.append(Issue(i, 1, 'SQL008', 'Hasło w plain text'))
    
    missing = tables_referenced - tables_created - {'dual', 'information_schema'}
    context = {'tables_created': list(tables_created), 'tables_referenced': list(tables_referenced), 'potentially_missing': list(missing)}
    return AnalysisResult('sql', code, '\n'.join(fixed_lines), errors, warnings, fixes, context)


def analyze_terraform(code: str) -> AnalysisResult:
    """Analyze Terraform."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    
    resources = []
    variables_defined = set()
    variables_used = set()
    providers = []
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if stripped.startswith('resource "'):
            match = re.search(r'resource\s+"([^"]+)"\s+"([^"]+)"', stripped)
            if match:
                resources.append({'type': match.group(1), 'name': match.group(2)})
        
        if stripped.startswith('variable "'):
            match = re.search(r'variable\s+"([^"]+)"', stripped)
            if match:
                variables_defined.add(match.group(1))
        
        for match in re.finditer(r'var\.(\w+)', stripped):
            variables_used.add(match.group(1))
        
        if stripped.startswith('provider "'):
            match = re.search(r'provider\s+"([^"]+)"', stripped)
            if match:
                providers.append(match.group(1))
        
        if re.search(r'(access_key|secret_key|password|token)\s*=\s*"[^"$]', stripped, re.I):
            errors.append(Issue(i, 1, 'TF001', 'Hardcoded credentials'))
        
        if 'cidr_blocks' in stripped and '0.0.0.0/0' in stripped:
            warnings.append(Issue(i, 1, 'TF002', '0.0.0.0/0 otwiera dostęp z internetu'))
        
        if 'encrypted' in stripped and 'false' in stripped:
            errors.append(Issue(i, 1, 'TF003', 'Wyłączone szyfrowanie'))
        
        if 'acl' in stripped and ('public-read' in stripped or 'public-read-write' in stripped):
            errors.append(Issue(i, 1, 'TF004', 'Publiczny bucket S3'))
    
    undefined = variables_used - variables_defined
    context = {'resources': resources, 'providers': providers, 'undefined_variables': list(undefined)}
    return AnalysisResult('terraform', code, code, errors, warnings, fixes, context)


def analyze_kubernetes(code: str) -> AnalysisResult:
    """Analyze Kubernetes YAML."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    
    kind = None
    namespace = None
    has_resources = False
    has_probes = False
    has_security_context = False
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if stripped.startswith('kind:'):
            kind = stripped.split(':')[1].strip()
        
        if stripped.startswith('namespace:'):
            namespace = stripped.split(':')[1].strip()
        
        if 'resources:' in stripped or 'limits:' in stripped or 'requests:' in stripped:
            has_resources = True
        
        if 'livenessProbe:' in stripped or 'readinessProbe:' in stripped:
            has_probes = True
        
        if 'securityContext:' in stripped:
            has_security_context = True
        
        if 'privileged: true' in stripped:
            errors.append(Issue(i, 1, 'K8S001', 'Kontener privileged'))
        
        if 'runAsUser: 0' in stripped:
            warnings.append(Issue(i, 1, 'K8S002', 'Kontener jako root'))
        
        if 'hostPath:' in stripped:
            warnings.append(Issue(i, 1, 'K8S003', 'hostPath - użyj PersistentVolume'))
        
        if 'image:' in stripped and (':latest' in stripped or ':' not in stripped.split('image:')[1]):
            warnings.append(Issue(i, 1, 'K8S004', 'Użyj konkretnego tagu'))
        
        if stripped.startswith('value:') and any(s in stripped.upper() for s in ['PASSWORD', 'SECRET', 'KEY']):
            errors.append(Issue(i, 1, 'K8S006', 'Hardcoded secret - użyj Secret'))
        
        if stripped == 'namespace: default':
            warnings.append(Issue(i, 1, 'K8S007', 'Użycie default namespace'))
    
    if kind in ('Deployment', 'Pod', 'StatefulSet'):
        if not has_resources:
            warnings.append(Issue(1, 1, 'K8S008', f'Brak resource limits dla {kind}'))
        if not has_probes:
            warnings.append(Issue(1, 1, 'K8S009', f'Brak probes dla {kind}'))
        if not has_security_context:
            warnings.append(Issue(1, 1, 'K8S010', f'Brak securityContext dla {kind}'))
    
    return AnalysisResult('kubernetes', code, code, errors, warnings, fixes, {'kind': kind, 'namespace': namespace})


def analyze_nginx(code: str) -> AnalysisResult:
    """Analyze nginx config."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    fixed_lines = lines.copy()
    
    has_ssl = False
    has_headers = False
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if 'ssl_certificate' in stripped:
            has_ssl = True
        if 'add_header' in stripped:
            has_headers = True
        
        if 'server_tokens on' in stripped:
            warnings.append(Issue(i, 1, 'NGINX001', 'server_tokens ujawnia wersję'))
            fixed = stripped.replace('server_tokens on', 'server_tokens off')
            fixes.append(Fix(i, 'Wyłączono server_tokens', stripped, fixed))
            fixed_lines[i-1] = line.replace(stripped, fixed)
        
        if 'autoindex on' in stripped:
            warnings.append(Issue(i, 1, 'NGINX002', 'autoindex ujawnia strukturę'))
        
        if 'ssl_protocols' in stripped and ('SSLv3' in stripped or 'TLSv1 ' in stripped):
            errors.append(Issue(i, 1, 'NGINX003', 'Słabe protokoły SSL'))
    
    if has_ssl and not has_headers:
        warnings.append(Issue(1, 1, 'NGINX005', 'Brak security headers'))
    
    return AnalysisResult('nginx', code, '\n'.join(fixed_lines), errors, warnings, fixes)


def analyze_github_actions(code: str) -> AnalysisResult:
    """Analyze GitHub Actions workflow."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    fixed_lines = lines.copy()
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if 'uses:' in stripped and ('@master' in stripped or '@main' in stripped):
            warnings.append(Issue(i, 1, 'GHA001', 'Użyj wersji/SHA zamiast @master'))
            fixed = re.sub(r'@(master|main)$', '@v4', stripped)
            fixes.append(Fix(i, 'Zmieniono na wersję', stripped, fixed))
            fixed_lines[i-1] = line.replace(stripped, fixed)
        
        if 'pull_request_target' in stripped:
            warnings.append(Issue(i, 1, 'GHA002', 'pull_request_target może być niebezpieczne'))
        
        if re.search(r'(password|token|key|secret)\s*[:=]\s*(?!\$\{\{)(?!\$\{)(?!\$)\S+', stripped, re.I):
            errors.append(Issue(i, 1, 'GHA003', 'Hardcoded secret - użyj ${{ secrets.NAME }}'))
        
        if '${{' in stripped and ('github.event.' in stripped or 'inputs.' in stripped):
            if 'run:' in stripped:
                warnings.append(Issue(i, 1, 'GHA004', 'Możliwy shell injection'))
        
        if stripped.startswith('jobs:'):
            warnings.append(Issue(i, 1, 'GHA005', 'Ustaw minimalne permissions'))
    
    return AnalysisResult('github-actions', code, '\n'.join(fixed_lines), errors, warnings, fixes)


def analyze_ansible(code: str) -> AnalysisResult:
    """Analyze Ansible playbook."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if re.search(r'password\s*:\s*["\']?[^\$\{]', stripped, re.I):
            errors.append(Issue(i, 1, 'ANS001', 'Plain text password - użyj ansible-vault'))
        
        if stripped.startswith('- shell:') or stripped.startswith('- command:'):
            if 'changed_when' not in '\n'.join(lines[i:min(i+5, len(lines))]):
                warnings.append(Issue(i, 1, 'ANS002', 'shell/command bez changed_when'))
        
        if 'become: true' in stripped or 'become: yes' in stripped:
            if 'become_user' not in '\n'.join(lines[max(0,i-3):i+3]):
                warnings.append(Issue(i, 1, 'ANS003', 'become bez become_user'))
        
        if 'ignore_errors: true' in stripped or 'ignore_errors: yes' in stripped:
            warnings.append(Issue(i, 1, 'ANS004', 'ignore_errors ukrywa błędy'))
    
    return AnalysisResult('ansible', code, code, errors, warnings, fixes)


# Import new analyzers
try:
    from .analyzers.typescript import analyze_typescript
    from .analyzers.go import analyze_go
    from .analyzers.rust import analyze_rust
    from .analyzers.java import analyze_java
    from .analyzers.csharp import analyze_csharp
    from .analyzers.ruby import analyze_ruby
    from .analyzers.makefile import analyze_makefile
    from .analyzers.yaml_generic import analyze_yaml
    from .analyzers.apache import analyze_apache
    from .analyzers.systemd import analyze_systemd
    from .analyzers.html import analyze_html
    from .analyzers.css import analyze_css
    from .analyzers.helm import analyze_helm
    from .analyzers.json_generic import analyze_json
    from .analyzers.toml_generic import analyze_toml
    from .analyzers.ini_generic import analyze_ini
    NEW_ANALYZERS_AVAILABLE = True
except ImportError:
    NEW_ANALYZERS_AVAILABLE = False


def analyze_code(code: str, filename: str = None, force_language: str = None) -> AnalysisResult:
    """Main entry point for code analysis."""
    language = force_language or detect_language(code, filename)
    
    analyzers = {
        'bash': analyze_bash,
        'python': analyze_python,
        'php': analyze_php,
        'javascript': lambda c: analyze_javascript(c, False),
        'nodejs': lambda c: analyze_javascript(c, True),
        'dockerfile': analyze_dockerfile,
        'docker-compose': analyze_docker_compose,
        'sql': analyze_sql,
        'terraform': analyze_terraform,
        'kubernetes': analyze_kubernetes,
        'nginx': analyze_nginx,
        'github-actions': analyze_github_actions,
        'ansible': analyze_ansible,
    }
    
    # Add new analyzers if available
    if NEW_ANALYZERS_AVAILABLE:
        analyzers.update({
            'typescript': analyze_typescript,
            'go': analyze_go,
            'rust': analyze_rust,
            'java': analyze_java,
            'csharp': analyze_csharp,
            'ruby': analyze_ruby,
            'makefile': analyze_makefile,
            'yaml': analyze_yaml,
            'apache': analyze_apache,
            'systemd': analyze_systemd,
            'html': analyze_html,
            'css': analyze_css,
            'helm': analyze_helm,
            'json': analyze_json,
            'toml': analyze_toml,
            'ini': analyze_ini,
        })
    
    analyzer = analyzers.get(language, analyze_bash)
    result = analyzer(code)
    result.language = language
    return result
