import re
from typing import List

from ..analyzer import Issue, Fix, AnalysisResult


def analyze_helm(code: str) -> AnalysisResult:
    """Analyze Helm-related YAML/templates for common issues."""
    errors: List[Issue] = []
    warnings: List[Issue] = []
    fixes: List[Fix] = []

    lines = code.split('\n')
    fixed_lines = lines.copy()

    lower_code = code.lower()
    is_chart = ('apiversion:' in lower_code and 'name:' in lower_code and 'version:' in lower_code)
    is_values = ('replicacount' in lower_code or 'image:' in lower_code or 'service:' in lower_code)
    is_template = ('{{' in code and '}}' in code)

    if is_values and is_template:
        warnings.append(Issue(1, 1, 'HELM001', 'Wykryto składnię templating w values.yaml - rozważ przeniesienie do templates/'))

    if is_chart:
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.lower().startswith('apiversion:'):
                val = stripped.split(':', 1)[1].strip().strip('"\'')
                if val != 'v2':
                    warnings.append(Issue(i, 1, 'HELM010', 'Chart.yaml: apiVersion powinno być v2'))
                    fixed = re.sub(r'(?i)^\s*apiVersion\s*:\s*.*$', 'apiVersion: v2', line)
                    fixes.append(Fix(i, 'Ustawiono apiVersion: v2', line.rstrip(), fixed.rstrip()))
                    fixed_lines[i - 1] = fixed

            if stripped.lower().startswith('version:'):
                ver = stripped.split(':', 1)[1].strip().strip('"\'')
                if ver and not re.match(r'^\d+\.\d+\.\d+([+-].+)?$', ver):
                    warnings.append(Issue(i, 1, 'HELM011', 'Chart.yaml: version powinien być SemVer (np. 1.2.3)'))

    if is_values:
        has_replica = False
        has_resources = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            indent_str = line[:indent]

            if stripped.startswith('replicaCount:'):
                has_replica = True
                m = re.search(r'\d+', stripped)
                if m and int(m.group()) <= 0:
                    warnings.append(Issue(i, 1, 'HELM020', 'replicaCount <= 0'))

            if re.match(r'^\s*tag\s*:\s*"?latest"?\s*$', stripped, re.I):
                warnings.append(Issue(i, 1, 'HELM021', 'image tag "latest" - utrudnia reprodukowalność'))
                fixed = f"{indent_str}tag: \"1.0.0\""
                fixes.append(Fix(i, 'Zmieniono tag: latest na 1.0.0', line.rstrip(), fixed.rstrip()))
                fixed_lines[i - 1] = fixed

            if re.match(r'^\s*imagePullPolicy\s*:\s*Always\s*$', stripped, re.I):
                warnings.append(Issue(i, 1, 'HELM022', 'imagePullPolicy: Always - rozważ IfNotPresent'))
                fixed = f"{indent_str}imagePullPolicy: IfNotPresent"
                fixes.append(Fix(i, 'Zmieniono imagePullPolicy na IfNotPresent', line.rstrip(), fixed.rstrip()))
                fixed_lines[i - 1] = fixed

            if re.match(r'^\s*type\s*:\s*LoadBalancer\s*$', stripped, re.I):
                prev = lines[i - 2].strip().lower() if i >= 2 else ''
                if prev.startswith('service') or any('service' in l.lower() and l.strip().endswith(':') for l in lines[max(0, i-6):i-1]):
                    warnings.append(Issue(i, 1, 'HELM023', 'service.type=LoadBalancer - może być niepożądane domyślnie'))
                    fixed = f"{indent_str}type: ClusterIP"
                    fixes.append(Fix(i, 'Zmieniono service.type na ClusterIP', line.rstrip(), fixed.rstrip()))
                    fixed_lines[i - 1] = fixed

            if stripped.startswith('resources:'):
                has_resources = True

        if not has_replica:
            warnings.append(Issue(1, 1, 'HELM024', 'Brak replicaCount - dodano domyślne replicaCount: 1'))
            fixed_lines.insert(0, 'replicaCount: 1')
            fixes.append(Fix(1, 'Dodano replicaCount: 1', '', 'replicaCount: 1'))

        if not has_resources:
            warnings.append(Issue(1, 1, 'HELM025', 'Brak resources requests/limits - dodano przykładowe wartości'))
            block = [
                '',
                'resources:',
                '  requests:',
                '    cpu: "100m"',
                '    memory: "128Mi"',
                '  limits:',
                '    cpu: "500m"',
                '    memory: "512Mi"',
            ]
            fixed_lines.extend(block)
            fixes.append(Fix(1, 'Dodano blok resources (requests/limits)', '', 'resources: ...'))

    if is_template:
        if re.search(r'\{\{\s*\.Values\.[A-Za-z0-9_.-]+\s*\}\}', code):
            warnings.append(Issue(1, 1, 'HELM030', 'Bezpośrednie użycie .Values.* bez default/required (może dawać nil)'))

        if re.search(r'image:\s*[^\s]+:latest', code):
            warnings.append(Issue(1, 1, 'HELM031', 'Hardcoded :latest w template - preferuj .Values.image.tag'))

    return AnalysisResult('helm', code, '\n'.join(fixed_lines), errors, warnings, fixes)
