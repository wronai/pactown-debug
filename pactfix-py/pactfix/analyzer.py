"""Multi-language code and config file analyzer."""

import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path

SUPPORTED_LANGUAGES = [
    'bash', 'python', 'php', 'javascript', 'nodejs',
    'dockerfile', 'docker-compose', 'sql', 'terraform',
    'kubernetes', 'nginx', 'github-actions', 'ansible'
]

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
            'fixes': [asdict(f) for f in self.fixes],
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
    
    if 'server {' in code or 'location ' in code:
        return 'nginx'
    
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
    
    return 'bash'


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


def analyze_bash(code: str) -> AnalysisResult:
    """Analyze Bash script."""
    errors, warnings, fixes = [], [], []
    lines = code.split('\n')
    fixed_lines = lines.copy()
    
    for i, line in enumerate(lines, 1):
        current_line = fixed_lines[i-1]
        stripped = current_line.strip()
        
        # Variables without braces: use ${VAR} for clarity (e.g. ${OUTPUT}/${HOST})
        if not stripped.startswith('#') and re.search(r'\$[A-Za-z_][A-Za-z0-9_]*', stripped):
            braced = _brace_unbraced_bash_vars(stripped)
            if braced != stripped:
                warnings.append(Issue(i, 1, 'BASH001', 'Zmienne bez klamerek: użyj składni ${VAR} (np. ${OUTPUT}/${HOST})'))
                fixes.append(Fix(i, 'Dodano klamerki do zmiennych', stripped, braced))
                current_line = current_line.replace(stripped, braced)
                stripped = braced
        
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
        stripped = line.strip()
        
        # Python 2 print statement
        if re.match(r'^print\s+["\']', stripped) or re.match(r'^print\s+\w', stripped):
            if not stripped.startswith('print('):
                errors.append(Issue(i, 1, 'PY001', 'Użyj print() z nawiasami (Python 3)'))
                match = re.match(r'^print\s+(.+)$', stripped)
                if match:
                    fixed = f'print({match.group(1)})'
                    fixes.append(Fix(i, 'Dodano nawiasy do print()', stripped, fixed))
                    fixed_lines[i-1] = line.replace(stripped, fixed)
        
        # Bare except
        if re.match(r'^except\s*:', stripped):
            warnings.append(Issue(i, 1, 'PY002', 'Unikaj pustego except: - złap konkretne wyjątki'))
        
        # Mutable default argument
        if re.search(r'def\s+\w+\s*\([^)]*=\s*(\[\]|\{\})', stripped):
            warnings.append(Issue(i, 1, 'PY003', 'Mutable default argument - użyj None'))
        
        # == None instead of is None
        if '== None' in stripped or '!= None' in stripped:
            warnings.append(Issue(i, 1, 'PY004', 'Użyj "is None" zamiast "== None"'))
    
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
    
    analyzer = analyzers.get(language, analyze_bash)
    result = analyzer(code)
    result.language = language
    return result
