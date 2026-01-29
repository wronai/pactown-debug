import re
import yaml
from typing import List, Dict, Any

from ..analyzer import Issue, Fix, AnalysisResult


def analyze_kubernetes(code: str) -> AnalysisResult:
    errors: List[Issue] = []
    warnings: List[Issue] = []
    fixes: List[Fix] = []

    lines = code.splitlines()
    fixed_lines = lines.copy()

    try:
        # Handle multi-document YAML
        documents = list(yaml.safe_load_all(code))
        if len(documents) == 1 and documents[0] is None:
            documents = []
    except yaml.YAMLError:
        return AnalysisResult('kubernetes', code, code, [Issue(1, 1, 'K8S999', 'Invalid YAML')], [], [])

    # Track line numbers for keys via simple scan
    key_line_map: Dict[str, int] = {}
    for i, line in enumerate(lines, 1):
        m = re.match(r'^\s*([a-zA-Z0-9_-]+)\s*:', line)
        if m:
            key_line_map[m.group(1)] = i

    # Process each document
    for doc in documents:
        if not isinstance(doc, dict):
            continue

        kind = doc.get('kind', '')
        metadata = doc.get('metadata', {})
        spec = doc.get('spec', {})
        
        # Check for namespace
        namespace = metadata.get('namespace', 'default')
        if namespace == 'default':
            ns_line = key_line_map.get('namespace')
            if ns_line:
                warnings.append(Issue(ns_line, 1, 'K8S007', 'Użycie default namespace'))

        # Analyze based on kind
        if kind in ('Deployment', 'Pod', 'StatefulSet', 'DaemonSet'):
            # Get pod spec
            if kind == 'Pod':
                pod_spec = spec
            else:
                pod_spec = spec.get('template', {}).get('spec', {})

            if not isinstance(pod_spec, dict):
                continue

            # Check containers
            containers = pod_spec.get('containers', [])
            if isinstance(containers, list):
                for idx, container in enumerate(containers):
                    if not isinstance(container, dict):
                        continue
                    
                    container_name = container.get('name')
                    container_display_name = container_name or f'container-{idx}'
                    
                    # Image tag fixes
                    image = container.get('image', '')
                    if image:
                        if ':latest' in image or ':' not in image:
                            # Find image line
                            if container_name:
                                img_line = _find_container_line(lines, container_name, 'image')
                            else:
                                img_line = _find_container_key_line_by_index(lines, idx, 'image')
                            if img_line:
                                warnings.append(Issue(img_line, 1, 'K8S004', 'Użyj konkretnego tagu'))
                                replacement = _suggest_image_tag(image)
                                if replacement != image:
                                    fixed_lines[img_line - 1] = fixed_lines[img_line - 1].replace(image, replacement)
                                    fixes.append(Fix(img_line, 'Zmieniono image na wersjonowany tag', f'image: {image}', f'image: {replacement}'))

                    # Security context checks
                    security_context = container.get('securityContext', {})
                    if isinstance(security_context, dict):
                        if security_context.get('privileged') is True:
                            if container_name:
                                priv_line = _find_container_line(lines, container_name, 'privileged')
                            else:
                                priv_line = _find_container_key_line_by_index(lines, idx, 'privileged')
                            if priv_line:
                                errors.append(Issue(priv_line, 1, 'K8S001', 'Kontener privileged'))
                                # Remove privileged: true
                                fixed_lines[priv_line - 1] = re.sub(r'^(\s*)privileged:\s*true.*$', r'\1# privileged: true - REMOVED', fixed_lines[priv_line - 1])
                                fixes.append(Fix(priv_line, 'Usunięto privileged: true', 'privileged: true', '# privileged: true - REMOVED'))

                        if security_context.get('runAsUser') == 0:
                            root_line = _find_container_line(lines, container_name, 'runAsUser')
                            if root_line:
                                warnings.append(Issue(root_line, 1, 'K8S002', 'Kontener jako root'))

                    # Resource limits
                    resources = container.get('resources', {})
                    if not isinstance(resources, dict) or not resources:
                        res_line = _find_container_line(lines, container_name, 'name')
                        if res_line:
                            warnings.append(Issue(res_line, 1, 'K8S008', f'Brak resource limits dla {kind}'))
                            # Add resource limits skeleton
                            indent = _get_line_indent(lines[res_line - 1])
                            skeleton = [
                                f'{indent}resources:',
                                f'{indent}  limits:',
                                f'{indent}    cpu: 500m',
                                f'{indent}    memory: 512Mi',
                                f'{indent}  requests:',
                                f'{indent}    cpu: 250m',
                                f'{indent}    memory: 256Mi'
                            ]
                            # Insert after container name or image
                            insert_line = res_line
                            if ':' in lines[res_line - 1]:
                                insert_line = res_line
                            else:
                                insert_line = res_line + 1
                            
                            for i, skel_line in enumerate(skeleton):
                                fixed_lines.insert(insert_line + i, skel_line)
                            
                            fixes.append(Fix(insert_line, 'Dodano resource limits', '', 'resources: [...]'))

                    # Probes
                    if not container.get('livenessProbe'):
                        probe_line = _find_container_line(lines, container_name, 'name')
                        if probe_line:
                            warnings.append(Issue(probe_line, 1, 'K8S009', f'Brak liveness probe dla {kind}'))
                            # Add liveness probe skeleton
                            indent = _get_line_indent(lines[probe_line - 1])
                            probe_skel = [
                                f'{indent}livenessProbe:',
                                f'{indent}  httpGet:',
                                f'{indent}    path: /health',
                                f'{indent}    port: 8080',
                                f'{indent}  initialDelaySeconds: 30',
                                f'{indent}  periodSeconds: 10'
                            ]
                            insert_pos = _find_insert_position(lines, probe_line, container_name)
                            for i, skel in enumerate(probe_skel):
                                fixed_lines.insert(insert_pos + i, skel)
                            fixes.append(Fix(insert_pos, 'Dodano liveness probe', '', 'livenessProbe: [...]'))

                    if not container.get('readinessProbe'):
                        probe_line = _find_container_line(lines, container_name, 'name')
                        if probe_line:
                            warnings.append(Issue(probe_line, 1, 'K8S009', f'Brak readiness probe dla {kind}'))
                            # Add readiness probe skeleton
                            indent = _get_line_indent(lines[probe_line - 1])
                            probe_skel = [
                                f'{indent}readinessProbe:',
                                f'{indent}  httpGet:',
                                f'{indent}    path: /ready',
                                f'{indent}    port: 8080',
                                f'{indent}  initialDelaySeconds: 5',
                                f'{indent}  periodSeconds: 5'
                            ]
                            insert_pos = _find_insert_position(lines, probe_line, container_name)
                            for i, skel in enumerate(probe_skel):
                                fixed_lines.insert(insert_pos + i, skel)
                            fixes.append(Fix(insert_pos, 'Dodano readiness probe', '', 'readinessProbe: [...]'))

            # Pod-level security context
            if not pod_spec.get('securityContext'):
                warnings.append(Issue(1, 1, 'K8S010', f'Brak pod-level securityContext dla {kind}'))
                # Add pod security context at the end of spec
                spec_line = key_line_map.get('spec')
                if spec_line:
                    indent = _get_line_indent(lines[spec_line - 1])
                    context_lines = [
                        f'{indent}securityContext:',
                        f'{indent}  runAsNonRoot: true',
                        f'{indent}  runAsUser: 1000',
                        f'{indent}  fsGroup: 2000'
                    ]
                    # Find where to insert (after containers or other spec fields)
                    insert_pos = spec_line + 1
                    while insert_pos < len(lines) and (lines[insert_pos].startswith(' ') or lines[insert_pos].strip() == ''):
                        insert_pos += 1
                    
                    for i, ctx_line in enumerate(context_lines):
                        fixed_lines.insert(insert_pos + i, ctx_line)
                    fixes.append(Fix(insert_pos, 'Dodano pod securityContext', '', 'securityContext: [...]'))

            # Check for hostPath volumes
            volumes = pod_spec.get('volumes', [])
            if isinstance(volumes, list):
                for volume in volumes:
                    if isinstance(volume, dict) and 'hostPath' in volume:
                        vol_line = key_line_map.get('hostPath')
                        if vol_line:
                            warnings.append(Issue(vol_line, 1, 'K8S003', 'hostPath - użyj PersistentVolume'))

        # Check for hardcoded secrets in any kind
        if 'value:' in code:
            for i, line in enumerate(lines, 1):
                if 'value:' in line:
                    stripped = line.strip()
                    if any(secret in stripped.upper() for secret in ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']):
                        if '${' not in line and 'valueFrom:' not in line:
                            errors.append(Issue(i, 1, 'K8S006', 'Hardcoded secret - użyj Secret'))

    return AnalysisResult('kubernetes', code, '\n'.join(fixed_lines), errors, warnings, fixes, {'kinds': [d.get('kind') for d in documents if isinstance(d, dict)]})


def _find_container_key_line_by_index(lines: List[str], container_index: int, key: str) -> int:
    """Find the line number for a key within the Nth container item in spec.containers.

    This is a fallback for minimal YAML inputs where a container may not have a `name:` field.
    """
    containers_line_idx = None
    containers_indent = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('containers:'):
            containers_line_idx = i
            containers_indent = len(line) - len(line.lstrip())
            break

    if containers_line_idx is None:
        return 0

    item_start_idx = None
    item_indent = 0
    item_count = -1
    for i in range(containers_line_idx + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())

        # Left containers list (next key in spec/etc.)
        if indent <= containers_indent and not line.lstrip().startswith('-'):
            break

        if line.lstrip().startswith('-'):
            item_count += 1
            if item_count == container_index:
                item_start_idx = i
                item_indent = indent
                break

    if item_start_idx is None:
        return 0

    key_re = re.compile(rf'^\s*(?:-\s*)?{re.escape(key)}\s*:')
    for j in range(item_start_idx, len(lines)):
        line = lines[j]
        if j > item_start_idx and line.strip():
            indent = len(line) - len(line.lstrip())
            if indent <= containers_indent and not line.lstrip().startswith('-'):
                break
            if line.lstrip().startswith('-') and indent == item_indent:
                break

        if key_re.search(line):
            return j + 1

    return 0


def _find_container_line(lines: List[str], container_name: str, key: str) -> int:
    """Find the line number for a specific key within a container definition."""
    in_container = False
    container_indent = 0
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        
        # Check for container start
        if f'name: {container_name}' in stripped:
            in_container = True
            container_indent = indent
            continue
        
        # Check if we've left the container
        if in_container and stripped and indent <= container_indent and not line.startswith(' '):
            in_container = False
            continue
        
        # Look for the key within container
        if in_container and f'{key}:' in stripped:
            return i
    
    return 0


def _get_line_indent(line: str) -> str:
    """Get the indentation of a line as spaces."""
    return line[:len(line) - len(line.lstrip())]


def _find_insert_position(lines: List[str], start_line: int, container_name: str) -> int:
    """Find a good position to insert new lines within a container."""
    container_indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
    
    for i in range(start_line, min(start_line + 20, len(lines))):
        line = lines[i]
        indent = len(line) - len(line.lstrip())
        
        # If we find a line with less or equal indentation that's not empty, we've left the container
        if line.strip() and indent <= container_indent and i > start_line:
            return i
    
    return start_line + 1


def _suggest_image_tag(image: str) -> str:
    """Suggest a specific version tag for an image."""
    if ':latest' in image:
        base = image[:-len(':latest')]
    elif ':' not in image:
        base = image
    else:
        return image
    
    # Common image suggestions
    suggestions = {
        'nginx': 'nginx:1.25',
        'redis': 'redis:7.2',
        'postgres': 'postgres:15.4',
        'mysql': 'mysql:8.1',
        'python': 'python:3.11',
        'node': 'node:20',
        'alpine': 'alpine:3.19',
        'ubuntu': 'ubuntu:22.04',
        'debian': 'debian:12',
        'centos': 'centos:9',
        'httpd': 'httpd:2.4',
        'busybox': 'busybox:1.36'
    }
    
    for name, suggested in suggestions.items():
        if base == name or base.endswith(f'/{name}'):
            return suggested
    
    # Default to a generic version
    return f"{base}:1.0.0"
