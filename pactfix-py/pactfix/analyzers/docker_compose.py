import re
import yaml
from typing import List, Dict, Any

from ..analyzer import Issue, Fix, AnalysisResult


def analyze_docker_compose(code: str) -> AnalysisResult:
    errors: List[Issue] = []
    warnings: List[Issue] = []
    fixes: List[Fix] = []

    lines = code.splitlines()
    fixed_lines = lines.copy()

    try:
        data = yaml.safe_load(code) or {}
    except yaml.YAMLError:
        return AnalysisResult('docker-compose', code, code, [Issue(1, 1, 'COMPOSE999', 'Invalid YAML')], [], [])

    services = data.get('services', {})
    networks = data.get('networks', {})
    has_networks = bool(networks)

    # Track line numbers for keys via simple scan
    key_line_map: Dict[str, int] = {}
    for i, line in enumerate(lines, 1):
        m = re.match(r'^\s*([a-zA-Z0-9_-]+)\s*:', line)
        if m:
            key_line_map[m.group(1)] = i

    for svc_name, svc in services.items():
        if not isinstance(svc, dict):
            continue

        # Image tag fixes
        image = svc.get('image', '')
        if image:
            if ':latest' in image or ':' not in image:
                # Determine line number for image key within this service
                svc_start_line = key_line_map.get(svc_name, 1)
                img_line = svc_start_line
                for j in range(svc_start_line, len(lines)):
                    if re.match(r'^\s*image\s*:', lines[j]):
                        img_line = j + 1
                        break
                warnings.append(Issue(img_line, 1, 'COMPOSE001', 'Użyj konkretnego tagu wersji'))
                replacement = image
                if image.startswith('alpine'):
                    replacement = 'alpine:3.19'
                elif image.startswith('python'):
                    replacement = 'python:3.11'
                elif image.startswith('node'):
                    replacement = 'node:20'
                elif image.startswith('nginx'):
                    replacement = 'nginx:1.25'
                else:
                    if image.endswith(':latest'):
                        replacement = image[:-len(':latest')] + ':1.0.0'
                    elif ':' not in image:
                        replacement = image + ':1.0.0'
                # Fix line
                indent_match = re.match(r'^(\s*)', lines[img_line - 1])
                indent = indent_match.group(0) if indent_match else ''
                fixed_lines[img_line - 1] = f'{indent}image: {replacement}'
                fixes.append(Fix(img_line, 'Zmieniono image na wersjonowany tag', f'image: {image}', f'image: {replacement}'))

        # Remove privileged: true
        if svc.get('privileged') is True:
            priv_line = key_line_map.get(svc_name, 1)
            for j in range(priv_line, len(lines)):
                if re.match(r'^\s*privileged\s*:\s*true', lines[j]):
                    errors.append(Issue(j + 1, 1, 'COMPOSE002', 'privileged: true jest niebezpieczne'))
                    fixed_lines[j] = ''
                    fixes.append(Fix(j + 1, 'Usunięto privileged: true', lines[j].strip(), ''))
                    break

        # Warn on network_mode: host
        if svc.get('network_mode') == 'host':
            nm_line = key_line_map.get(svc_name, 1)
            for j in range(nm_line, len(lines)):
                if re.match(r'^\s*network_mode\s*:\s*host', lines[j]):
                    warnings.append(Issue(j + 1, 1, 'COMPOSE003', 'network_mode: host omija izolację'))
                    break

        # Warn on docker.sock mount
        volumes = svc.get('volumes', [])
        for vol in volumes:
            if isinstance(vol, str) and '/var/run/docker.sock' in vol:
                v_line = key_line_map.get(svc_name, 1)
                for j in range(v_line, len(lines)):
                    if '/var/run/docker.sock' in lines[j]:
                        errors.append(Issue(j + 1, 1, 'COMPOSE004', 'Montowanie docker.sock daje pełny dostęp'))
                        break

        # Hardcoded secrets in environment
        env = svc.get('environment', {})
        secret_patterns = ['PASSWORD', 'SECRET', 'API_KEY', 'TOKEN']
        if isinstance(env, dict):
            for k, v in env.items():
                if any(p in k.upper() for p in secret_patterns) and isinstance(v, str) and not v.startswith('${'):
                    env_line = key_line_map.get(svc_name, 1)
                    for j in range(env_line, len(lines)):
                        if f'{k}:' in lines[j]:
                            errors.append(Issue(j + 1, 1, 'COMPOSE005', 'Hardcoded secret - użyj .env'))
                            break
        elif isinstance(env, list):
            for item in env:
                if not isinstance(item, str):
                    continue
                if '=' not in item:
                    continue
                k, v = item.split('=', 1)
                k = k.strip()
                v = v.strip()
                if not k:
                    continue
                if any(p in k.upper() for p in secret_patterns) and v and not v.startswith('${'):
                    env_line = key_line_map.get(svc_name, 1)
                    for j in range(env_line, len(lines)):
                        if item in lines[j]:
                            errors.append(Issue(j + 1, 1, 'COMPOSE005', 'Hardcoded secret - użyj .env'))
                            break

    # Add networks block if missing and more than 1 service
    if len(services) > 1 and not has_networks:
        warnings.append(Issue(1, 1, 'COMPOSE006', f'Zdefiniuj networks dla {len(services)} serwisów'))
        # Append minimal networks block
        fixed_lines.append('')
        fixed_lines.append('networks:')
        fixed_lines.append('  default:')
        fixed_lines.append('    driver: bridge')
        fixes.append(Fix(len(lines) + 2, 'Dodano sieć domyślną', '', 'networks:'))

    return AnalysisResult('docker-compose', code, '\n'.join(fixed_lines), errors, warnings, fixes, {'services': list(services.keys())})
